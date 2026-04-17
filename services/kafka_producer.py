from __future__ import annotations

import json
import logging
from typing import Any

from kafka import KafkaProducer


logger = logging.getLogger(__name__)


class KafkaEventProducer:
    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self.topic = topic
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            key_serializer=lambda value: value.encode("utf-8") if value else None,
        )

    def send(self, payload: dict[str, Any], key: str | None = None) -> None:
        future = self._producer.send(self.topic, key=key, value=payload)
        metadata = future.get(timeout=10)
        logger.info(
            "Published event to topic=%s partition=%s offset=%s",
            metadata.topic,
            metadata.partition,
            metadata.offset,
        )

    def close(self) -> None:
        self._producer.flush()
        self._producer.close()
