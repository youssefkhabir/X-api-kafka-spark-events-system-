from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import joblib
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    current_timestamp,
    explode,
    from_json,
    struct,
    to_json,
    udf,
    window,
)
from pyspark.sql.types import (
    IntegerType,
    StringType,
    StructField,
    StructType,
    ArrayType,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics.sentiment import extract_hashtags, lexicon_label, lexicon_score


def build_spark_session() -> SparkSession:
    return (
        SparkSession.builder.appName("KafkaSparkSentiment")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )


def build_schema() -> StructType:
    return StructType(
        [
            StructField("id", StringType(), False),
            StructField("source", StringType(), True),
            StructField("text", StringType(), False),
            StructField("lang", StringType(), True),
            StructField("author_id", StringType(), True),
            StructField("created_at", StringType(), True),
        ]
    )


def maybe_load_model(model_path: Path):
    if model_path.exists():
        return joblib.load(model_path)
    return None


def _is_wsl() -> bool:
    if os.getenv("WSL_DISTRO_NAME"):
        return True

    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def _resolve_windows_host_from_wsl() -> str | None:
    try:
        for line in Path("/etc/resolv.conf").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "nameserver":
                return parts[1]
    except OSError:
        return None

    return None


def normalize_kafka_bootstrap_servers(bootstrap_servers: str) -> str:
    if not _is_wsl():
        return bootstrap_servers

    windows_host = _resolve_windows_host_from_wsl()
    if not windows_host:
        return bootstrap_servers

    normalized_servers: list[str] = []
    for server in bootstrap_servers.split(","):
        value = server.strip()
        if not value:
            continue

        host, separator, port = value.rpartition(":")
        if not separator:
            normalized_servers.append(value)
            continue

        if host in {"localhost", "127.0.0.1", "::1", "[::1]"}:
            normalized_servers.append(f"{windows_host}:{port}")
            continue

        normalized_servers.append(value)

    return ",".join(normalized_servers) if normalized_servers else bootstrap_servers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kafka-bootstrap", default="localhost:9092")
    parser.add_argument("--topic", default="raw_posts")
    parser.add_argument("--predictions-topic", default="predictions")
    parser.add_argument("--checkpoint", default="checkpoints/spark_sentiment")
    parser.add_argument("--model-path", default="models/sentiment_model.joblib")
    args = parser.parse_args()
    kafka_bootstrap = normalize_kafka_bootstrap_servers(args.kafka_bootstrap)

    if kafka_bootstrap != args.kafka_bootstrap:
        print(f"Resolved Kafka bootstrap servers for WSL: {kafka_bootstrap}")

    spark = build_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    raw_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", kafka_bootstrap)
        .option("subscribe", args.topic)
        .option("startingOffsets", "latest")
        .load()
    )

    schema = build_schema()
    parsed = raw_stream.selectExpr("CAST(value AS STRING) AS json_payload").select(
        from_json(col("json_payload"), schema).alias("event")
    )

    events = parsed.select("event.*").withColumn("ingested_at", current_timestamp())

    score_udf = udf(lexicon_score, IntegerType())
    label_udf = udf(lexicon_label, StringType())
    hashtags_udf = udf(lambda text: list(extract_hashtags(text)), ArrayType(StringType()))

    enriched = (
        events.withColumn("lexicon_score", score_udf(col("text")))
        .withColumn("lexicon_sentiment", label_udf(col("text")))
        .withColumn("hashtags", hashtags_udf(col("text")))
    )

    model = maybe_load_model(Path(args.model_path))
    if model is not None:
        predict_udf = udf(lambda text: str(model.predict([text])[0]), StringType())
        enriched = enriched.withColumn("ml_sentiment", predict_udf(col("text")))

    sentiment_counts = (
        enriched.groupBy(window(col("ingested_at"), "30 seconds"), col("lexicon_sentiment"))
        .count()
        .selectExpr(
            "CAST(window.start AS STRING) AS window_start",
            "CAST(window.end AS STRING) AS window_end",
            "lexicon_sentiment",
            "count",
        )
    )

    hashtag_counts = (
        enriched.withColumn("hashtag", explode(col("hashtags")))
        .groupBy(window(col("ingested_at"), "30 seconds"), col("hashtag"))
        .count()
        .selectExpr(
            "CAST(window.start AS STRING) AS window_start",
            "CAST(window.end AS STRING) AS window_end",
            "hashtag",
            "count",
        )
    )

    sentiment_query = (
        sentiment_counts.writeStream.outputMode("complete")
        .format("console")
        .option("truncate", "false")
        .option("checkpointLocation", f"{args.checkpoint}/sentiment")
        .start()
    )

    hashtag_query = (
        hashtag_counts.writeStream.outputMode("complete")
        .format("console")
        .option("truncate", "false")
        .option("checkpointLocation", f"{args.checkpoint}/hashtags")
        .start()
    )

    prediction_payload = enriched.select(
        col("id").alias("key"),
        to_json(
            struct(
                col("id"),
                col("source"),
                col("text"),
                col("lang"),
                col("author_id"),
                col("created_at"),
                col("ingested_at"),
                col("lexicon_score"),
                col("lexicon_sentiment"),
                col("hashtags"),
                *([col("ml_sentiment")] if "ml_sentiment" in enriched.columns else []),
            )
        ).alias("value"),
    )

    predictions_query = (
        prediction_payload.selectExpr(
            "CAST(key AS STRING) AS key",
            "CAST(value AS STRING) AS value",
        )
        .writeStream.outputMode("append")
        .format("kafka")
        .option("kafka.bootstrap.servers", kafka_bootstrap)
        .option("topic", args.predictions_topic)
        .option("checkpointLocation", f"{args.checkpoint}/predictions")
        .start()
    )

    try:
        spark.streams.awaitAnyTermination()
    finally:
        for query in (sentiment_query, hashtag_query, predictions_query):
            if query.isActive:
                query.stop()


if __name__ == "__main__":
    main()
