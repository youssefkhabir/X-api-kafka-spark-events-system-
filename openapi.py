from __future__ import annotations

from typing import Any


def build_openapi_spec(base_url: str) -> dict[str, Any]:
    return {
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
                    "description": "Render the live analytics dashboard.",
                    "responses": {"200": {"description": "HTML dashboard page."}},
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
                                        "bluesky_api_base_url": "https://public.api.bsky.app",
                                        "bluesky_query": "spark kafka flask",
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
                            "schema": {"type": "integer", "minimum": 1, "maximum": 100},
                            "description": "Maximum number of sample messages to publish.",
                        },
                        {
                            "name": "delay",
                            "in": "query",
                            "schema": {"type": "number", "format": "float", "minimum": 0, "maximum": 10},
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
                        },
                        "400": {"description": "Invalid query parameters."},
                        "502": {"description": "Kafka publishing failure."},
                    },
                }
            },
            "/publish/bluesky": {
                "post": {
                    "summary": "Fetch recent Bluesky posts and publish them into Kafka",
                    "responses": {
                        "200": {
                            "description": "Bluesky messages published successfully.",
                            "content": {
                                "application/json": {
                                    "example": {"published": 10, "topic": "raw_posts"}
                                }
                            },
                        },
                        "502": {"description": "Remote Bluesky API failure or Kafka publishing failure."},
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
                    "responses": {"200": {"description": "Interactive Swagger UI page."}},
                }
            },
        },
    }
