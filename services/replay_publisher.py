from __future__ import annotations

import json
import time
from pathlib import Path

from services.kafka_producer import KafkaEventProducer


def replay_sample_posts(
    producer: KafkaEventProducer,
    sample_file: Path,
    delay_seconds: float = 1.0,
    limit: int | None = None,
) -> int:
    published = 0
    with sample_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            producer.send(payload, key=payload.get("id"))
            published += 1
            if limit is not None and published >= limit:
                break
            time.sleep(delay_seconds)
    return published
