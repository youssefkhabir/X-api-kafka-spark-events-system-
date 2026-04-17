from __future__ import annotations

import argparse
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kafka-bootstrap", default="localhost:9092")
    parser.add_argument("--topic", default="raw_posts")
    parser.add_argument("--predictions-topic", default="predictions")
    parser.add_argument("--checkpoint", default="checkpoints/spark_sentiment")
    parser.add_argument("--model-path", default="models/sentiment_model.joblib")
    args = parser.parse_args()

    spark = build_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    raw_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", args.kafka_bootstrap)
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
        .option("kafka.bootstrap.servers", args.kafka_bootstrap)
        .option("topic", args.predictions_topic)
        .option("checkpointLocation", f"{args.checkpoint}/predictions")
        .start()
    )

    sentiment_query.awaitTermination()
    hashtag_query.awaitTermination()
    predictions_query.awaitTermination()


if __name__ == "__main__":
    main()
