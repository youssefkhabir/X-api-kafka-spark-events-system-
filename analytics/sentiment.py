from __future__ import annotations

import re
from typing import Iterable


POSITIVE_WORDS = {"good", "great", "love", "awesome", "fast", "happy", "excellent", "win"}
NEGATIVE_WORDS = {"bad", "hate", "slow", "terrible", "bug", "broken", "sad", "fail"}


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b[a-zA-Z']+\b", text.lower())


def lexicon_score(text: str) -> int:
    tokens = tokenize(text)
    positive = sum(1 for token in tokens if token in POSITIVE_WORDS)
    negative = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    return positive - negative


def lexicon_label(text: str) -> str:
    score = lexicon_score(text)
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"


def extract_hashtags(text: str) -> Iterable[str]:
    return re.findall(r"#(\w+)", text.lower())
