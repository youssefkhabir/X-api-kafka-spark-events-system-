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

    X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")
    X_QUERY = os.getenv("X_QUERY", "(spark OR kafka OR flask) lang:en -is:retweet")
    X_SEARCH_MAX_RESULTS = int(os.getenv("X_SEARCH_MAX_RESULTS", "10"))

    SAMPLE_DATA_PATH = BASE_DIR / "data" / "sample_posts.jsonl"
    MODEL_PATH = BASE_DIR / os.getenv("MODEL_PATH", "models/sentiment_model.joblib")
