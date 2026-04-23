from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

import requests


DEFAULT_API_BASE_URL = "https://api.bsky.app"
SEARCH_PATH = "/xrpc/app.bsky.feed.searchPosts"
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "kafka-events-system/1.0 (+local dev)",
}
FALLBACK_API_BASE_URLS = {
    "https://public.api.bsky.app": "https://api.bsky.app",
}


class BlueskyClient:
    def __init__(self, api_base_url: str, query: str, limit: int = 10) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.query = query
        self.limit = limit

    def search_recent_posts(self) -> list[dict[str, Any]]:
        response = self._search_posts(self.api_base_url)

        payload = response.json()
        events = []
        for item in payload.get("posts", []):
            author = item.get("author", {})
            record = item.get("record", {})
            events.append(
                {
                    "id": item.get("uri", f"bsky-{author.get('did', 'unknown')}-{item.get('indexedAt', datetime.now(UTC).isoformat())}"),
                    "source": "bluesky_api",
                    "text": record.get("text", ""),
                    "lang": record.get("langs", ["und"])[0] if record.get("langs") else "und",
                    "author_id": author.get("did", "unknown"),
                    "author_handle": author.get("handle", "unknown"),
                    "created_at": item.get("indexedAt") or record.get("createdAt") or datetime.now(UTC).isoformat(),
                    "metrics": {
                        "reply_count": item.get("replyCount", 0),
                        "repost_count": item.get("repostCount", 0),
                        "like_count": item.get("likeCount", 0),
                        "quote_count": item.get("quoteCount", 0),
                    },
                }
            )
        return events

    def _search_posts(self, api_base_url: str) -> requests.Response:
        response = requests.get(
            f"{api_base_url}{SEARCH_PATH}",
            params={
                "q": self.query,
                "limit": self.limit,
            },
            headers=DEFAULT_HEADERS,
            timeout=30,
        )

        fallback_api_base_url = FALLBACK_API_BASE_URLS.get(api_base_url)
        if response.status_code == 403 and fallback_api_base_url:
            fallback_response = requests.get(
                f"{fallback_api_base_url}{SEARCH_PATH}",
                params={
                    "q": self.query,
                    "limit": self.limit,
                },
                headers=DEFAULT_HEADERS,
                timeout=30,
            )
            fallback_response.raise_for_status()
            return fallback_response

        response.raise_for_status()
        return response
