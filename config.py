from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "raw_posts")
    KAFKA_TOPIC_PREDICTIONS = os.getenv("KAFKA_TOPIC_PREDICTIONS", "predictions")

    BLUESKY_API_BASE_URL = os.getenv("BLUESKY_API_BASE_URL", "https://api.bsky.app")
    BLUESKY_QUERY = os.getenv("BLUESKY_QUERY", "spark kafka flask")
    BLUESKY_SEARCH_LIMIT = int(os.getenv("BLUESKY_SEARCH_LIMIT", "10"))

    SAMPLE_DATA_PATH = BASE_DIR / "data" / "sample_posts.jsonl"
    MODEL_PATH = BASE_DIR / os.getenv("MODEL_PATH", "models/sentiment_model.joblib")
