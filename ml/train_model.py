from __future__ import annotations

from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


TRAINING_DATA = [
    ("I love building streaming dashboards with Spark", "positive"),
    ("Kafka is awesome for event-driven apps", "positive"),
    ("This Flask demo is fast and great", "positive"),
    ("The API response is terrible and slow", "negative"),
    ("I hate when the pipeline is broken", "negative"),
    ("This bug makes the app fail badly", "negative"),
    ("The post is about data engineering", "neutral"),
    ("We are collecting public messages about technology", "neutral"),
    ("Spark and Kafka are tools for stream processing", "neutral"),
]


def main() -> None:
    texts = [row[0] for row in TRAINING_DATA]
    labels = [row[1] for row in TRAINING_DATA]

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
            ("classifier", LogisticRegression(max_iter=500)),
        ]
    )
    pipeline.fit(texts, labels)

    model_path = Path("models/sentiment_model.joblib")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)
    print(f"Saved model to {model_path}")


if __name__ == "__main__":
    main()
