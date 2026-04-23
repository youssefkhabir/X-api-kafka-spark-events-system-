from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from time import monotonic
from typing import Any

from kafka import KafkaConsumer, TopicPartition
from kafka.errors import KafkaError


CACHE_TTL_SECONDS = 3.0
_SUMMARY_CACHE: dict[tuple[str, str, str], tuple[float, dict[str, Any]]] = {}


def _decode_json_payload(raw: bytes) -> dict[str, Any] | None:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _build_consumer(bootstrap_servers: str) -> KafkaConsumer:
    return KafkaConsumer(
        bootstrap_servers=bootstrap_servers,
        enable_auto_commit=False,
        consumer_timeout_ms=1500,
        value_deserializer=_decode_json_payload,
        key_deserializer=lambda raw: raw.decode("utf-8") if raw else None,
    )


def read_recent_messages(bootstrap_servers: str, topic: str, limit: int = 200) -> list[dict[str, Any]]:
    consumer = _build_consumer(bootstrap_servers)
    try:
        partitions = consumer.partitions_for_topic(topic)
        if not partitions:
            return []

        topic_partitions = [TopicPartition(topic, partition) for partition in sorted(partitions)]
        consumer.assign(topic_partitions)
        consumer.poll(timeout_ms=200)

        end_offsets = consumer.end_offsets(topic_partitions)
        start_offsets = {}
        per_partition_limit = max(1, limit // max(1, len(topic_partitions)))

        for topic_partition in topic_partitions:
            end_offset = end_offsets[topic_partition]
            start_offsets[topic_partition] = max(0, end_offset - per_partition_limit)
            consumer.seek(topic_partition, start_offsets[topic_partition])

        messages: list[dict[str, Any]] = []
        while len(messages) < limit:
            batch = consumer.poll(timeout_ms=300)
            if not batch:
                break
            for records in batch.values():
                for record in records:
                    payload = record.value
                    if payload is not None:
                        messages.append(payload)
                    if len(messages) >= limit:
                        break
                if len(messages) >= limit:
                    break

        return sorted(messages, key=lambda item: item.get("ingested_at", item.get("created_at", "")))
    finally:
        consumer.close()


def _safe_parse_timestamp(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        normalized = raw_value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def build_dashboard_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    sentiment_counter: Counter[str] = Counter()
    hashtag_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    timeline: dict[str, int] = defaultdict(int)

    for event in events:
        sentiment = event.get("ml_sentiment") or event.get("lexicon_sentiment") or "unknown"
        sentiment_counter[sentiment] += 1
        source_counter[event.get("source", "unknown")] += 1

        for hashtag in event.get("hashtags", []):
            hashtag_counter[hashtag] += 1

        timestamp = _safe_parse_timestamp(event.get("ingested_at")) or _safe_parse_timestamp(event.get("created_at"))
        if timestamp is not None:
            timeline[timestamp.strftime("%H:%M:%S")] += 1

    total_events = len(events)
    positive = sentiment_counter.get("positive", 0)
    negative = sentiment_counter.get("negative", 0)
    neutral = sentiment_counter.get("neutral", 0)

    return {
        "total_events": total_events,
        "sentiments": {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "unknown": sentiment_counter.get("unknown", 0),
        },
        "sources": dict(source_counter),
        "top_hashtags": [{"tag": tag, "count": count} for tag, count in hashtag_counter.most_common(6)],
        "timeline": [{"time": label, "count": timeline[label]} for label in sorted(timeline.keys())],
        "latest_events": list(reversed(events[-8:])),
        "health": {
            "sentiment_balance": positive - negative,
            "positive_ratio": round((positive / total_events) * 100, 1) if total_events else 0.0,
            "negative_ratio": round((negative / total_events) * 100, 1) if total_events else 0.0,
        },
    }


def read_dashboard_summary(bootstrap_servers: str, predictions_topic: str, raw_topic: str) -> dict[str, Any]:
    cache_key = (bootstrap_servers, predictions_topic, raw_topic)
    cached = _SUMMARY_CACHE.get(cache_key)
    now = monotonic()
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    try:
        events = read_recent_messages(bootstrap_servers, predictions_topic, limit=200)
        active_topic = predictions_topic
        if not events:
            events = read_recent_messages(bootstrap_servers, raw_topic, limit=200)
            active_topic = raw_topic
        summary = build_dashboard_summary(events)
        summary["active_topic"] = active_topic
        summary["mode"] = "processed" if active_topic == predictions_topic else "fallback_raw"
        _SUMMARY_CACHE[cache_key] = (now, summary)
        return summary
    except KafkaError as exc:
        summary = {
            "total_events": 0,
            "sentiments": {"positive": 0, "negative": 0, "neutral": 0, "unknown": 0},
            "sources": {},
            "top_hashtags": [],
            "timeline": [],
            "latest_events": [],
            "health": {"sentiment_balance": 0, "positive_ratio": 0.0, "negative_ratio": 0.0},
            "active_topic": predictions_topic,
            "mode": "unavailable",
            "error": str(exc),
        }
        _SUMMARY_CACHE[cache_key] = (now, summary)
        return summary
