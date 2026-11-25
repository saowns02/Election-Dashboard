"""Minimal client for the Wikimedia REST API with disk caching.

Wikipedia election articles are edited in near-real time on election night,
which makes them a practical free "live" source for all three countries.
We use the REST endpoint (``/api/rest_v1/page/html/<title>``) because it is
the documented, cache-friendly way to read rendered article HTML.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests

API = "https://en.wikipedia.org/api/rest_v1/page/html/{title}"
USER_AGENT = os.environ.get(
    "ELECTION_DASHBOARD_UA",
    "ElectionDashboard/1.0 (https://github.com/saowns02/Election-Dashboard)",
)
CACHE_DIR = Path(os.environ.get("ELECTION_CACHE_DIR", Path(__file__).resolve().parent.parent / "data" / "cache"))


class WikiError(RuntimeError):
    pass


@dataclass
class Page:
    title: str          # canonical title after redirects
    html: str
    fetched_at: float   # unix time the HTML was downloaded
    revision: str | None = None


def _cache_path(title: str) -> Path:
    key = hashlib.sha1(title.encode()).hexdigest()[:16]
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", title)[:80]
    return CACHE_DIR / f"{safe}-{key}.json"


def _read_cache(title: str) -> Page | None:
    p = _cache_path(title)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return Page(d["title"], d["html"], d["fetched_at"], d.get("revision"))
    except Exception:
        return None


def _write_cache(requested: str, page: Page) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(requested).write_text(
            json.dumps({"title": page.title, "html": page.html,
                        "fetched_at": page.fetched_at, "revision": page.revision}),
            encoding="utf-8")
    except OSError:
        pass  # read-only filesystem (e.g. some hosts): just skip caching


def fetch(title: str, max_age: float = 3600, retries: int = 4, timeout: float = 30) -> Page:
    """Return the article HTML, from cache if younger than ``max_age`` seconds.

    On HTTP 429/5xx it backs off and retries; if every attempt fails it falls
    back to a stale cached copy before giving up.
    """
    title = title.replace(" ", "_")
    cached = _read_cache(title)
    if cached and time.time() - cached.fetched_at < max_age:
        return cached

    url = API.format(title=requests.utils.quote(title, safe=""))
    delay = 5.0
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
                             timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                canonical = title
                m = re.search(r'<link rel="dc:isVersionOf" href="//en\.wikipedia\.org/wiki/([^"]+)"', r.text)
                if m:
                    canonical = requests.utils.unquote(m.group(1))
                page = Page(canonical, r.text, time.time(), r.headers.get("ETag"))
                _write_cache(title, page)
                return page
            if r.status_code == 404:
                raise WikiError(f"Wikipedia page not found: {title}")
            last_err = WikiError(f"HTTP {r.status_code} for {title}")
            retry_after = r.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
        except requests.RequestException as e:
            last_err = e
            wait = delay
        if attempt < retries - 1:
            time.sleep(min(wait, 60))
            delay *= 2
    if cached:
        return cached  # stale but better than nothing
    raise WikiError(str(last_err))
