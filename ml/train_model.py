from __future__ import annotations

import argparse
import csv
import html
import json
import random
import re
import urllib.request
import zipfile
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


DATASET_URL = "http://cs.stanford.edu/people/alecmgo/trainingandtestdata.zip"
DATASET_DIR = Path("data") / "sentiment140"
DATASET_ZIP_PATH = DATASET_DIR / "trainingandtestdata.zip"
TRAINING_CSV_PATH = DATASET_DIR / "training.1600000.processed.noemoticon.csv"
SAMPLED_CSV_PATH = DATASET_DIR / "sentiment140_binary_50k.csv"
MODEL_PATH = Path("models") / "sentiment_model.joblib"
METRICS_PATH = Path("models") / "sentiment_model_metrics.json"

LABEL_MAP = {
    0: "negative",
    4: "positive",
}

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
USER_PATTERN = re.compile(r"@\w+")
WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_tweet(text: str) -> str:
    text = html.unescape(text)
    text = URL_PATTERN.sub(" URL ", text)
    text = USER_PATTERN.sub(" USER ", text)
    text = text.replace("&amp;", " and ")
    text = WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def download_dataset() -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    if not DATASET_ZIP_PATH.exists():
        print(f"Downloading Sentiment140 dataset from {DATASET_URL}...")
        urllib.request.urlretrieve(DATASET_URL, DATASET_ZIP_PATH)

    if TRAINING_CSV_PATH.exists():
        return

    print(f"Extracting dataset into {DATASET_DIR}...")
    with zipfile.ZipFile(DATASET_ZIP_PATH) as archive:
        archive.extractall(DATASET_DIR)


def iter_binary_rows(csv_path: Path):
    with csv_path.open(encoding="ISO-8859-1", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if len(row) != 6:
                continue
            raw_label, _tweet_id, _date, _query, _user, text = row
            try:
                label = LABEL_MAP[int(raw_label)]
            except (KeyError, ValueError):
                continue

            normalized_text = normalize_tweet(text)
            if normalized_text:
                yield normalized_text, label


def build_balanced_sample(csv_path: Path, sample_size: int, random_seed: int) -> list[tuple[str, str]]:
    if sample_size < 2:
        raise ValueError("sample_size must be at least 2.")
    if sample_size % 2 != 0:
        raise ValueError("sample_size must be even for balanced binary sampling.")

    reservoir_size = sample_size // 2
    rng = random.Random(random_seed)
    reservoirs: dict[str, list[str]] = {"negative": [], "positive": []}
    seen: dict[str, int] = {"negative": 0, "positive": 0}

    for text, label in iter_binary_rows(csv_path):
        seen[label] += 1
        reservoir = reservoirs[label]
        if len(reservoir) < reservoir_size:
            reservoir.append(text)
            continue

        replacement_index = rng.randint(0, seen[label] - 1)
        if replacement_index < reservoir_size:
            reservoir[replacement_index] = text

    if any(len(items) < reservoir_size for items in reservoirs.values()):
        raise RuntimeError("Dataset did not contain enough binary examples to satisfy the requested sample size.")

    sample = [(text, label) for label, texts in reservoirs.items() for text in texts]
    rng.shuffle(sample)
    return sample


def save_sample_csv(sample: list[tuple[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["text", "label"])
        writer.writerows(sample)


def train_model(sample: list[tuple[str, str]], test_size: float, random_seed: int):
    texts = [text for text, _label in sample]
    labels = [label for _text, label in sample]

    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=test_size,
        random_state=random_seed,
        stratify=labels,
    )

    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.98,
                    sublinear_tf=True,
                    max_features=100_000,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1_000,
                    solver="liblinear",
                    random_state=random_seed,
                ),
            ),
        ]
    )

    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)

    precision, recall, f1, _support = precision_recall_fscore_support(
        y_test,
        predictions,
        pos_label="positive",
        average="binary",
        zero_division=0,
    )

    metrics = {
        "sample_size": len(sample),
        "train_size": len(x_train),
        "test_size": len(x_test),
        "labels": sorted(set(labels)),
        "accuracy": accuracy_score(y_test, predictions),
        "precision_positive": precision,
        "recall_positive": recall,
        "f1_positive": f1,
        "confusion_matrix": confusion_matrix(
            y_test,
            predictions,
            labels=["negative", "positive"],
        ).tolist(),
        "classification_report": classification_report(
            y_test,
            predictions,
            labels=["negative", "positive"],
            output_dict=True,
            zero_division=0,
        ),
    }

    return pipeline, metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the tweet sentiment classifier from Sentiment140.")
    parser.add_argument("--sample-size", type=int, default=50_000, help="Balanced binary sample size to train on.")
    parser.add_argument("--test-size", type=float, default=0.2, help="Fraction of the sample reserved for testing.")
    parser.add_argument("--random-seed", type=int, default=42, help="Random seed for sampling and splitting.")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Assume the Sentiment140 training CSV already exists locally.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.skip_download:
        download_dataset()
    elif not TRAINING_CSV_PATH.exists():
        raise FileNotFoundError(f"Missing dataset file: {TRAINING_CSV_PATH}")

    print(f"Building balanced binary sample of {args.sample_size} rows from {TRAINING_CSV_PATH}...")
    sample = build_balanced_sample(TRAINING_CSV_PATH, args.sample_size, args.random_seed)
    save_sample_csv(sample, SAMPLED_CSV_PATH)

    print("Training logistic regression sentiment model...")
    model, metrics = train_model(sample, args.test_size, args.random_seed)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"Saved model to {MODEL_PATH}")
    print(f"Saved metrics to {METRICS_PATH}")
    print(f"Saved sampled dataset to {SAMPLED_CSV_PATH}")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Precision (positive): {metrics['precision_positive']:.4f}")
    print(f"Recall (positive): {metrics['recall_positive']:.4f}")
    print(f"F1 (positive): {metrics['f1_positive']:.4f}")
    print("Confusion matrix [negative, positive]:")
    for row in metrics["confusion_matrix"]:
        print(row)


if __name__ == "__main__":
    main()
