from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

import requests


SEARCH_URL = "https://api.x.com/2/tweets/search/recent"


class XClient:
    def __init__(self, bearer_token: str, query: str, max_results: int = 10) -> None:
        self.bearer_token = bearer_token
        self.query = query
        self.max_results = max_results

    def search_recent_posts(self) -> list[dict[str, Any]]:
        if not self.bearer_token:
            raise ValueError("X_BEARER_TOKEN is missing.")

        response = requests.get(
            SEARCH_URL,
            headers={"Authorization": f"Bearer {self.bearer_token}"},
            params={
                "query": self.query,
                "max_results": self.max_results,
                "tweet.fields": "created_at,lang,public_metrics,author_id",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        events = []
        for post in payload.get("data", []):
            metrics = post.get("public_metrics", {})
            events.append(
                {
                    "id": post["id"],
                    "source": "x_api",
                    "text": post["text"],
                    "lang": post.get("lang", "und"),
                    "author_id": post.get("author_id", "unknown"),
                    "created_at": post.get("created_at", datetime.now(UTC).isoformat()),
                    "metrics": {
                        "retweet_count": metrics.get("retweet_count", 0),
                        "reply_count": metrics.get("reply_count", 0),
                        "like_count": metrics.get("like_count", 0),
                        "quote_count": metrics.get("quote_count", 0),
                    },
                }
            )
        return events
