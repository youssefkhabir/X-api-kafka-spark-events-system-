from __future__ import annotations

import logging
from http import HTTPStatus

from flask import Flask, jsonify, render_template, request
from kafka.errors import KafkaError
import requests

from config import Config
from services.dashboard_service import read_dashboard_summary
from services.kafka_producer import KafkaEventProducer
from services.replay_publisher import replay_sample_posts
from services.x_client import XClient


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
    return jsonify(
        {
            "openapi": "3.0.3",
            "info": {
                "title": "Kafka Events System API",
                "version": "1.0.0",
                "description": "Flask endpoints for publishing events to Kafka and exposing the project dashboard.",
            },
            "servers": [{"url": base_url}],
            "paths": {
                "/": {
                    "get": {
                        "summary": "Dashboard page",
                        "description": "Render the presentation dashboard.",
                        "responses": {
                            "200": {"description": "HTML dashboard page."}
                        },
                    }
                },
                "/health": {
                    "get": {
                        "summary": "Health check",
                        "responses": {
                            "200": {
                                "description": "Application health and key runtime settings.",
                                "content": {
                                    "application/json": {
                                        "example": {
                                            "status": "ok",
                                            "kafka_bootstrap_servers": "localhost:9092",
                                            "raw_topic": "raw_posts",
                                            "sample_data_path": "D:/.../data/sample_posts.jsonl",
                                            "x_configured": False,
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                "/publish/sample": {
                    "post": {
                        "summary": "Replay sample events into Kafka",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer", "minimum": 1},
                                "description": "Maximum number of sample messages to publish.",
                            },
                            {
                                "name": "delay",
                                "in": "query",
                                "schema": {"type": "number", "format": "float", "minimum": 0},
                                "description": "Delay in seconds between two events.",
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "Messages published successfully.",
                                "content": {
                                    "application/json": {
                                        "example": {"published": 6, "topic": "raw_posts"}
                                    }
                                },
                            }
                        },
                    }
                },
                "/publish/x": {
                    "post": {
                        "summary": "Fetch recent X posts and publish them into Kafka",
                        "responses": {
                            "200": {
                                "description": "X messages published successfully.",
                                "content": {
                                    "application/json": {
                                        "example": {"published": 10, "topic": "raw_posts"}
                                    }
                                },
                            },
                            "400": {"description": "Missing bearer token or invalid local configuration."},
                            "502": {"description": "Remote X API failure or Kafka publishing failure."},
                        },
                    }
                },
                "/api/dashboard/summary": {
                    "get": {
                        "summary": "Dashboard summary JSON",
                        "responses": {
                            "200": {
                                "description": "Current dashboard aggregates based on recent Kafka messages."
                            }
                        },
                    }
                },
                "/api/dashboard/events": {
                    "get": {
                        "summary": "Latest dashboard events",
                        "responses": {
                            "200": {
                                "description": "A compact payload containing the latest visible events."
                            }
                        },
                    }
                },
                "/api/docs": {
                    "get": {
                        "summary": "Swagger UI",
                        "responses": {
                            "200": {"description": "Interactive Swagger UI page."}
                        },
                    }
                },
            },
        }
    )


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
            "x_configured": bool(app.config["X_BEARER_TOKEN"]),
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
    producer = build_producer()
    try:
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
        producer.close()

    return jsonify({"published": published, "topic": app.config["KAFKA_TOPIC_RAW"]})


@app.post("/publish/x")
def publish_from_x():
    client = XClient(
        bearer_token=app.config["X_BEARER_TOKEN"],
        query=app.config["X_QUERY"],
        max_results=app.config["X_SEARCH_MAX_RESULTS"],
    )
    producer = build_producer()
    try:
        posts = client.search_recent_posts()
        for post in posts:
            producer.send(post, key=post["id"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except requests.RequestException as exc:  # type: ignore[name-defined]
        return jsonify({"error": f"X API request failed: {exc}"}), HTTPStatus.BAD_GATEWAY
    except KafkaError as exc:
        return jsonify({"error": f"Kafka publish failed: {exc}"}), HTTPStatus.BAD_GATEWAY
    finally:
        producer.close()

    return jsonify({"published": len(posts), "topic": app.config["KAFKA_TOPIC_RAW"]})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
