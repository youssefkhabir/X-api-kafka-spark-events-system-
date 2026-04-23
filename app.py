from __future__ import annotations

import logging
from http import HTTPStatus

from flask import Flask, jsonify, render_template, request
from kafka.errors import KafkaError
import requests

from services.bluesky_client import BlueskyClient
from config import Config
from openapi import build_openapi_spec
from services.dashboard_service import read_dashboard_summary
from services.kafka_producer import KafkaEventProducer
from services.replay_publisher import replay_sample_posts


logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config.from_object(Config)


def build_producer() -> KafkaEventProducer:
    return KafkaEventProducer(
        bootstrap_servers=app.config["KAFKA_BOOTSTRAP_SERVERS"],
        topic=app.config["KAFKA_TOPIC_RAW"],
    )


@app.get("/")
def index():
    return render_template("index.html", config=app.config)


@app.get("/api/openapi.json")
def openapi_spec():
    base_url = request.host_url.rstrip("/")
    return jsonify(build_openapi_spec(base_url))


@app.get("/api/docs")
def api_docs():
    return render_template("swagger_ui.html", openapi_url="/api/openapi.json")


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "kafka_bootstrap_servers": app.config["KAFKA_BOOTSTRAP_SERVERS"],
            "raw_topic": app.config["KAFKA_TOPIC_RAW"],
            "sample_data_path": str(app.config["SAMPLE_DATA_PATH"]),
            "bluesky_api_base_url": app.config["BLUESKY_API_BASE_URL"],
            "bluesky_query": app.config["BLUESKY_QUERY"],
        }
    )


@app.get("/api/dashboard/summary")
def dashboard_summary():
    summary = read_dashboard_summary(
        bootstrap_servers=app.config["KAFKA_BOOTSTRAP_SERVERS"],
        predictions_topic=app.config["KAFKA_TOPIC_PREDICTIONS"],
        raw_topic=app.config["KAFKA_TOPIC_RAW"],
    )
    return jsonify(summary)


@app.get("/api/dashboard/events")
def dashboard_events():
    summary = read_dashboard_summary(
        bootstrap_servers=app.config["KAFKA_BOOTSTRAP_SERVERS"],
        predictions_topic=app.config["KAFKA_TOPIC_PREDICTIONS"],
        raw_topic=app.config["KAFKA_TOPIC_RAW"],
    )
    return jsonify(
        {
            "active_topic": summary.get("active_topic"),
            "mode": summary.get("mode"),
            "events": summary.get("latest_events", []),
            "error": summary.get("error"),
        }
    )


@app.post("/publish/sample")
def publish_sample():
    limit = request.args.get("limit", type=int)
    delay = request.args.get("delay", default=1.0, type=float)
    if limit is not None and (limit < 1 or limit > 100):
        return jsonify({"error": "limit must be between 1 and 100."}), HTTPStatus.BAD_REQUEST
    if delay < 0 or delay > 10:
        return jsonify({"error": "delay must be between 0 and 10 seconds."}), HTTPStatus.BAD_REQUEST

    producer = None
    try:
        producer = build_producer()
        published = replay_sample_posts(
            producer=producer,
            sample_file=app.config["SAMPLE_DATA_PATH"],
            delay_seconds=delay,
            limit=limit,
        )
    except FileNotFoundError:
        return jsonify({"error": "Sample data file not found."}), HTTPStatus.NOT_FOUND
    except KafkaError as exc:
        return jsonify({"error": f"Kafka publish failed: {exc}"}), HTTPStatus.BAD_GATEWAY
    finally:
        if producer is not None:
            producer.close()

    return jsonify({"published": published, "topic": app.config["KAFKA_TOPIC_RAW"]})


@app.post("/publish/bluesky")
def publish_from_bluesky():
    client = BlueskyClient(
        api_base_url=app.config["BLUESKY_API_BASE_URL"],
        query=app.config["BLUESKY_QUERY"],
        limit=app.config["BLUESKY_SEARCH_LIMIT"],
    )
    producer = None
    try:
        posts = client.search_recent_posts()
        producer = build_producer()
        for post in posts:
            producer.send(post, key=post["id"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except requests.RequestException as exc:  # type: ignore[name-defined]
        return jsonify({"error": f"Bluesky API request failed: {exc}"}), HTTPStatus.BAD_GATEWAY
    except KafkaError as exc:
        return jsonify({"error": f"Kafka publish failed: {exc}"}), HTTPStatus.BAD_GATEWAY
    finally:
        if producer is not None:
            producer.close()

    return jsonify({"published": len(posts), "topic": app.config["KAFKA_TOPIC_RAW"]})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
