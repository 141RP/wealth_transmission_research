"""A small, polite HTTP client: rate limited, retrying, caching raw pages."""

from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime
from pathlib import Path

import requests

from . import config


class BackupWindowError(RuntimeError):
    """Raised when the court's nightly backup window is in effect."""


def in_backup_window(now: datetime | None = None) -> bool:
    now = (now or datetime.now(config.COURT_TZ)).astimezone(config.COURT_TZ)
    return now.hour >= config.BACKUP_START_HOUR or now.hour < config.BACKUP_END_HOUR


class PoliteClient:
    def __init__(self, cache_dir: Path | str = "data/raw", min_interval: float | None = None,
                 use_cache: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval = config.MIN_SECONDS_BETWEEN_REQUESTS if min_interval is None else min_interval
        self.use_cache = use_cache
        self._last_request = 0.0
        contact = os.environ.get("PROBATE_SCRAPER_CONTACT", "")
        self.session = requests.Session()
        self.session.headers["User-Agent"] = config.USER_AGENT.format(
            contact=f"; contact: {contact}" if contact else "")
        self.requests_made = 0

    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / (hashlib.sha256(url.encode()).hexdigest()[:20] + ".html")

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def get(self, url: str) -> str:
        """Return the page's HTML, from cache when we already fetched it."""
        path = self._cache_path(url)
        if self.use_cache and path.exists():
            return path.read_text(encoding="utf-8")
        if in_backup_window():
            raise BackupWindowError(
                "The court's search is offline for backup between 10 PM and 2 AM Eastern. Try later.")
        last_error: Exception | None = None
        for attempt in range(config.MAX_RETRIES):
            self._wait()
            self._last_request = time.monotonic()
            self.requests_made += 1
            try:
                resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT_SECONDS)
            except requests.RequestException as exc:
                last_error = exc
            else:
                if resp.status_code == 200 and "upstream connect error" not in resp.text[:300]:
                    path.write_text(resp.text, encoding="utf-8")
                    return resp.text
                if resp.status_code in (403, 429):
                    # Being told to stop is final: don't hammer the court.
                    raise RuntimeError(f"Server refused the request ({resp.status_code}); stopping.")
                last_error = RuntimeError(f"HTTP {resp.status_code} for {url}")
            time.sleep(self.min_interval * (2 ** attempt))
        raise RuntimeError(f"Giving up on {url}: {last_error}")
