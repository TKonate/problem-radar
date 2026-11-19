"""Collectors: public APIs and feeds, behind one small HTTP client.

Rules of the house (they are also in the README):

* only public, documented endpoints: no scraping, no login, no bypass;
* one request at a time per host, with a visible minimum interval;
* a descriptive ``User-Agent``;
* a hard cap on what is read (``limit``) and on response size;
* every failure is reported, never silently swallowed.

The HTTP layer is injectable (:class:`Transport`) so the whole collection logic
is testable without network access.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from . import __version__
from .config import SourceConfig
from .errors import CollectionError
from .models import Signal
from .taxonomy import SOURCE_TIERS
from .text import clip, extract_problem, infer_category, infer_domain, is_problem_like

#: User-Agent sent with every request (identifies the tool, no tracking).
USER_AGENT = f"problem-radar/{__version__} (+https://github.com/TKonate/problem-radar)"

#: Default minimum delay between two requests to the same host, in seconds.
#: GitHub's unauthenticated search API allows 10 requests per minute.
DEFAULT_MIN_INTERVALS: dict[str, float] = {
    "api.github.com": 6.0,
    "hn.algolia.com": 1.0,
}

#: Maximum response body we accept, in bytes (1 MiB is far enough for a feed).
MAX_RESPONSE_BYTES = 1_048_576


@dataclass
class HttpResponse:
    """Minimal HTTP response used by the collectors."""

    status: int
    body: str
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)


class Transport(Protocol):
    """Anything that can perform a GET request."""

    def get(self, url: str, headers: dict[str, str], timeout: float) -> HttpResponse: ...


class UrllibTransport:
    """Standard library transport."""

    def __init__(self, max_bytes: int = MAX_RESPONSE_BYTES) -> None:
        self.max_bytes = max_bytes

    def get(self, url: str, headers: dict[str, str], timeout: float) -> HttpResponse:
        """Perform the request, turning HTTP errors into a response object."""
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read(self.max_bytes)
                return HttpResponse(
                    status=int(response.status),
                    body=raw.decode("utf-8", errors="replace"),
                    url=response.geturl(),
                    headers={key.lower(): value for key, value in response.headers.items()},
                )
        except HTTPError as exc:
            body = ""
            try:
                body = exc.read(8192).decode("utf-8", errors="replace")
            except Exception:  # pragma: no cover - best effort error body
                pass
            return HttpResponse(
                status=int(exc.code),
                body=body,
                url=url,
                headers={key.lower(): value for key, value in (exc.headers or {}).items()},
            )


class HttpClient:
    """Polite HTTP client: rate limit, retries and readable errors."""

    def __init__(
        self,
        transport: Transport | None = None,
        *,
        timeout: float = 15.0,
        retries: int = 2,
        min_intervals: dict[str, float] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.transport = transport or UrllibTransport()
        self.timeout = timeout
        self.retries = retries
        self.min_intervals = dict(DEFAULT_MIN_INTERVALS if min_intervals is None else min_intervals)
        self.sleep = sleep
        self._last_call: dict[str, float] = {}
        self._clock = time.monotonic

    def _throttle(self, host: str) -> None:
        """Sleep for the remainder of the per-host interval, if any.

        The clock is monotonic so a wall-clock adjustment cannot cause a burst
        of requests. The first call to a host is never delayed.
        """
        interval = self.min_intervals.get(host, 1.0)
        previous = self._last_call.get(host)
        if previous is not None:
            elapsed = self._clock() - previous
            if elapsed < interval:
                self.sleep(interval - elapsed)
        self._last_call[host] = self._clock()

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """GET ``url`` with throttling and retries on transient errors.

        Raises:
            CollectionError: On a definitive failure (4xx, exhausted retries,
                network error).
        """
        if params:
            separator = "&" if urlsplit(url).query else "?"
            url = f"{url}{separator}{urlencode(params)}"

        host = urlsplit(url).hostname or ""
        request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json, text/xml, */*"}
        request_headers.update(headers or {})

        last_error = ""
        for attempt in range(self.retries + 1):
            self._throttle(host)
            try:
                response = self.transport.get(url, request_headers, self.timeout)
            except (URLError, TimeoutError, OSError) as exc:
                last_error = f"network error: {exc}"
            else:
                if response.status == 200:
                    return response
                if response.status in {429, 500, 502, 503, 504}:
                    # Retry-After is the only correct answer to a 429; it is
                    # capped so a hostile or broken header cannot stall a cron
                    # run for minutes.
                    retry_after = response.headers.get("retry-after", "")
                    delay = float(retry_after) if retry_after.isdigit() else float(2**attempt)
                    last_error = f"HTTP {response.status}"
                    if attempt < self.retries:
                        self.sleep(min(delay, 30.0))
                        continue
                elif response.status in {401, 403}:
                    hint = (
                        " (GitHub: set GITHUB_TOKEN to raise the search rate limit)"
                        if host == "api.github.com"
                        else ""
                    )
                    raise CollectionError(
                        f"HTTP {response.status} on {url}{hint}",
                        url=url,
                        status=response.status,
                    )
                elif response.status == 404:
                    raise CollectionError(f"not found: {url}", url=url, status=404)
                else:
                    last_error = f"HTTP {response.status}"
            if attempt < self.retries:
                self.sleep(float(2**attempt))

        raise CollectionError(f"request failed ({last_error}): {url}", url=url)

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """GET and decode a JSON document."""
        response = self.get(url, params, headers=headers)
        try:
            return json.loads(response.body)
        except json.JSONDecodeError as exc:
            raise CollectionError(
                f"invalid JSON from {response.url or url}: {exc}", url=url
            ) from exc

    def get_text(self, url: str, *, headers: dict[str, str] | None = None) -> str:
        """GET and return a text document."""
        return self.get(url, headers=headers).body


@dataclass
class CollectionResult:
    """Outcome of one collector run.

    Attributes:
        signals: New signals, already normalised and filtered.
        collected: Items read before filtering.
        filtered: Items dropped because they do not describe a problem.
        errors: Non-fatal errors (one query failed but others succeeded).
    """

    signals: list[Signal] = field(default_factory=list)
    collected: int = 0
    filtered: int = 0
    errors: list[str] = field(default_factory=list)


def _iso_date(value: str) -> str:
    """Best-effort ISO date from an RFC 2822 or ISO 8601 string."""
    if not value:
        return ""
    text = value.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(text).date().isoformat()
    except (TypeError, ValueError):
        return text[:10] if len(text) >= 10 else ""


def _make_signal(
    *,
    source: str,
    source_id: str,
    url: str,
    title: str,
    body: str = "",
    author: str = "",
    published_at: str = "",
    tier: str = "unknown",
    extra_tags: list[str] | None = None,
) -> Signal:
    """Build a normalised signal with inferred domain and category."""
    # Data minimisation: keep a short excerpt, not the whole issue thread.
    body = clip(body, 2000)
    problem, evidence = extract_problem(title, body)
    combined = f"{title} {body}"
    tags: list[str] = sorted({tier, *[str(tag) for tag in (extra_tags or [])]})
    return Signal(
        source=source,
        source_id=source_id,
        url=url,
        title=title,
        body=body,
        author=author,
        published_at=_iso_date(published_at),
        domain=infer_domain(combined),
        category=infer_category(combined),
        problem=problem,
        evidence=evidence,
        confidence=SOURCE_TIERS.get(tier, SOURCE_TIERS["unknown"]),
        tags=tags,
    )


def collect_hackernews(
    source: SourceConfig, client: HttpClient, *, limit: int | None = None
) -> CollectionResult:
    """Collect Hacker News stories through the public Algolia API.

    Endpoint: ``https://hn.algolia.com/api/v1/search`` (documented, no key).
    """
    result = CollectionResult()
    per_query = limit or source.limit
    for query in source.queries:
        try:
            payload = client.get_json(
                "https://hn.algolia.com/api/v1/search",
                {
                    "query": query,
                    "tags": "story",
                    "hitsPerPage": per_query,
                },
            )
        except CollectionError as exc:
            result.errors.append(f"hackernews {query!r}: {exc}")
            continue

        for hit in (payload.get("hits", []) or [])[:per_query]:
            title = str(hit.get("title") or "").strip()
            if not title:
                continue
            result.collected += 1
            body = str(hit.get("story_text") or "")
            if not is_problem_like(title):
                result.filtered += 1
                continue
            object_id = str(hit.get("objectID") or "")
            # The same article is often submitted several times: keep one signal
            # per article, the thread link stays the evidence.
            article_url = str(hit.get("url") or "").strip()
            result.signals.append(
                _make_signal(
                    source="hackernews",
                    source_id=article_url or object_id,
                    url=f"https://news.ycombinator.com/item?id={object_id}",
                    title=title,
                    body=body,
                    author=str(hit.get("author") or ""),
                    published_at=str(hit.get("created_at") or ""),
                    tier=source.tier,
                    extra_tags=[f"query:{query}"],
                )
            )
    return result


def collect_github(
    source: SourceConfig, client: HttpClient, *, limit: int | None = None
) -> CollectionResult:
    """Collect GitHub issues through the public search API.

    Unauthenticated requests are limited to 10 per minute; set ``GITHUB_TOKEN``
    (read-only, never stored) to raise the limit. Labels are kept as tags.
    """
    import os

    result = CollectionResult()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    per_query = limit or source.limit
    for query in source.queries:
        try:
            payload = client.get_json(
                "https://api.github.com/search/issues",
                {"q": query, "sort": "created", "order": "desc", "per_page": per_query},
                headers=headers,
            )
        except CollectionError as exc:
            result.errors.append(f"github {query!r}: {exc}")
            continue

        for item in (payload.get("items", []) or [])[:per_query]:
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            result.collected += 1
            body = str(item.get("body") or "")
            if not is_problem_like(title):
                result.filtered += 1
                continue
            repository = str(item.get("repository_url") or "").rsplit("/", 2)[-2:]
            repo_name = "/".join(repository)
            labels = [str(label.get("name", "")).lower() for label in item.get("labels", []) or []]
            result.signals.append(
                _make_signal(
                    source="github",
                    source_id=f"{repo_name}#{item.get('number')}",
                    url=str(item.get("html_url") or ""),
                    title=title,
                    body=body,
                    author=str((item.get("user") or {}).get("login") or ""),
                    published_at=str(item.get("created_at") or ""),
                    tier=source.tier,
                    extra_tags=[f"repo:{repo_name}", *labels],
                )
            )
    return result


def _local_name(tag: str) -> str:
    """Strip an XML namespace from a tag name."""
    return tag.rsplit("}", 1)[-1].lower()


def parse_feed(text: str) -> list[dict[str, str]]:
    """Parse an RSS 2.0 or Atom feed into plain dictionaries.

    Returns:
        One dictionary per item, carrying the keys found among ``title``,
        ``link``, ``summary``, ``author`` and ``published``; absent elements are
        simply missing from the dictionary.

    Raises:
        CollectionError: On malformed XML.
    """
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise CollectionError(f"invalid feed: {exc}") from exc

    items: list[dict[str, str]] = []
    for element in root.iter():
        if _local_name(element.tag) not in {"item", "entry"}:
            continue
        item: dict[str, str] = {}
        for child in element:
            name = _local_name(child.tag)
            text_value = (child.text or "").strip()
            if name == "title":
                item["title"] = text_value
            elif name == "link":
                item["link"] = child.get("href") or text_value
            elif name in {"description", "summary", "content"} and "summary" not in item:
                item["summary"] = text_value
            elif name in {"pubdate", "published", "updated"} and "published" not in item:
                item["published"] = text_value
            elif name in {"creator", "author"} and "author" not in item:
                author_name = next(
                    (grand.text for grand in child if _local_name(grand.tag) == "name"), None
                )
                item["author"] = (author_name or text_value).strip()
        items.append(item)
    return items


def collect_rss(
    source: SourceConfig, client: HttpClient, *, limit: int | None = None
) -> CollectionResult:
    """Collect items from the configured Atom/RSS feeds."""
    result = CollectionResult()
    per_feed = limit or source.limit
    for feed in source.feeds:
        try:
            items = parse_feed(client.get_text(feed))
        except CollectionError as exc:
            result.errors.append(f"rss {feed}: {exc}")
            continue

        for item in items[:per_feed]:
            title = (item.get("title") or "").strip()
            if not title:
                continue
            result.collected += 1
            body = item.get("summary") or ""
            if not is_problem_like(title):
                result.filtered += 1
                continue
            link = item.get("link") or feed
            result.signals.append(
                _make_signal(
                    source="rss",
                    source_id=link,
                    url=link,
                    title=title,
                    body=body,
                    author=item.get("author", ""),
                    published_at=item.get("published", ""),
                    tier=source.tier,
                    extra_tags=[f"feed:{urlsplit(feed).hostname or feed}"],
                )
            )
    return result


def collect_manual(
    source: SourceConfig, client: HttpClient, *, base_dir: Path, limit: int | None = None
) -> CollectionResult:
    """Read hand-written signals from a JSONL file.

    Each line is an object with at least ``source_id``, ``title`` and ``url``;
    every :class:`~problem_radar.models.Signal` field may be supplied, and the
    missing ones are inferred exactly like for the network collectors. A
    ``domain`` or ``category`` given in the line is copied as-is, without
    validation against the taxonomy, because a hand-written entry is trusted.
    """
    result = CollectionResult()
    path = Path(source.path or "data/manual-signals.jsonl")
    if not path.is_absolute():
        path = base_dir / path
    if not path.is_file():
        result.errors.append(f"manual file not found: {path}")
        return result

    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            result.errors.append(f"manual line {number}: invalid JSON ({exc})")
            continue
        title = str(payload.get("title", "")).strip()
        if not title:
            result.errors.append(f"manual line {number}: missing title")
            continue
        result.collected += 1
        if not is_problem_like(title):
            result.filtered += 1
            continue
        signal = _make_signal(
            source=str(payload.get("source", "manual")),
            source_id=str(payload.get("source_id") or payload.get("url") or f"line-{number}"),
            url=str(payload.get("url", "")),
            title=title,
            body=str(payload.get("body", "")),
            author=str(payload.get("author", "")),
            published_at=str(payload.get("published_at", "")),
            tier=str(payload.get("tier", source.tier)),
            extra_tags=[str(tag) for tag in payload.get("tags", [])],
        )
        if payload.get("domain"):
            signal.domain = str(payload["domain"])
        if payload.get("category"):
            signal.category = str(payload["category"])
        result.signals.append(signal)
        if limit and len(result.signals) >= limit:
            break
    return result


def collect_source(
    source: SourceConfig,
    client: HttpClient,
    *,
    base_dir: Path | None = None,
    limit: int | None = None,
) -> CollectionResult:
    """Run the collector matching ``source.kind``."""
    if source.kind == "hackernews":
        return collect_hackernews(source, client, limit=limit)
    if source.kind == "github":
        return collect_github(source, client, limit=limit)
    if source.kind == "rss":
        return collect_rss(source, client, limit=limit)
    if source.kind == "manual":
        return collect_manual(source, client, base_dir=base_dir or Path.cwd(), limit=limit)
    raise CollectionError(f"no collector for kind {source.kind!r}", source=source.name)
