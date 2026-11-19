"""Text helpers: normalisation, similarity and problem extraction.

Everything is rule based and inspectable. No model, no network: a signal must be
explainable by the text it contains, otherwise it is not a signal.
"""

from __future__ import annotations

import re
import unicodedata

from .taxonomy import CATEGORY_KEYWORDS, DOMAIN_KEYWORDS, SEVERITY_WORDS, STOPWORDS

_TOKEN = re.compile(r"[a-z0-9][a-z0-9+#._-]*")

#: Prefixes and boilerplate removed from titles before comparison.
_TITLE_NOISE = re.compile(
    r"^\s*(\[(bug|feature|rfc|discussion|question|help|idea)[^\]]*\]|"
    r"\(?(ask|show|tell|launch)\s+hn\)?\s*:?|"
    r"(bug|feature|rfc|question)\s*:\s*)",
    re.IGNORECASE,
)

#: Sentence split used for evidence extraction. Good enough for titles/bodies.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def fold(text: str) -> str:
    """Lowercase and strip accents so ``souverainetés`` matches ``souverainetes``."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


def clip(text: str, limit: int = 400) -> str:
    """Truncate ``text`` on a word boundary, adding an ellipsis when cut.

    Whitespace is collapsed first, so the result is always a single line.
    """
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip()
    return f"{cut}…"


def tokens(text: str, extra_stopwords: frozenset[str] | None = None) -> set[str]:
    """Return the meaningful tokens of ``text``.

    Tokens shorter than three characters are dropped except a short allow-list
    (``ai``, ``db``, ``ui``, ``os``, ``ci``) that carries meaning in this
    domain, where dropping them would erase the subject of a title.
    """
    stopwords = STOPWORDS | (extra_stopwords or frozenset())
    found = set(_TOKEN.findall(fold(text)))
    return {
        token
        for token in found
        if token not in stopwords
        and not token.isdigit()
        and (len(token) >= 3 or token in {"ai", "db", "ui", "os", "ci"})
    }


def clean_title(title: str) -> str:
    """Remove aggregator prefixes and normalise whitespace."""
    cleaned = _TITLE_NOISE.sub("", title)
    return " ".join(cleaned.split()).strip(" -:–—|")


def jaccard(first: set[str], second: set[str]) -> float:
    """Jaccard similarity of two token sets."""
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def containment(first: set[str], second: set[str]) -> float:
    """Share of the smaller set contained in the larger one."""
    if not first or not second:
        return 0.0
    return len(first & second) / min(len(first), len(second))


def similarity(first: str, second: str) -> float:
    """Similarity of two texts in ``[0, 1]``.

    A weighted mix of Jaccard (both formulations matter) and containment (one
    title is often a short version of the other).
    """
    first_tokens = tokens(first)
    second_tokens = tokens(second)
    return 0.6 * jaccard(first_tokens, second_tokens) + 0.4 * containment(
        first_tokens, second_tokens
    )


def first_sentence(text: str, limit: int = 300) -> str:
    """Return the first non-empty sentence of ``text``, clipped.

    Sentences of twenty characters or less are skipped as noise; when none
    qualifies, the whole text is clipped instead.
    """
    for sentence in _SENTENCE_SPLIT.split(text or ""):
        sentence = sentence.strip()
        if len(sentence) > 20:
            return clip(sentence, limit)
    return clip(text or "", limit)


def severity_hits(text: str) -> set[str]:
    """Return the severity words present in ``text``.

    Matching is plain substring, unlike :func:`has_keyword`, so a word also
    fires inside a longer one (``leak`` matches ``bleak``).
    """
    folded = fold(text)
    return {word for word in SEVERITY_WORDS if word in folded}


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    """Compile a keyword match that respects word boundaries.

    Substring matching is too loose for a taxonomy: "bug" would match "debug",
    "api" would match "capital", and every issue would look like a bug report.
    """
    escaped = re.escape(keyword.lower())
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


_KEYWORD_CACHE: dict[str, re.Pattern[str]] = {}


def has_keyword(text: str, keyword: str) -> bool:
    """True when ``keyword`` appears as a whole word in the folded ``text``."""
    pattern = _KEYWORD_CACHE.get(keyword)
    if pattern is None:
        pattern = _keyword_pattern(keyword)
        _KEYWORD_CACHE[keyword] = pattern
    return bool(pattern.search(text))


def infer_domain(text: str) -> str:
    """Infer a domain from keywords, ``other`` when nothing matches."""
    folded = fold(text)
    scores = {
        domain: sum(1 for keyword in keywords if has_keyword(folded, keyword))
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    best = max(scores, key=lambda domain: scores[domain])
    return best if scores[best] > 0 else "other"


def infer_category(text: str) -> str:
    """Infer a category from keywords, ``other`` when nothing matches."""
    folded = fold(text)
    scores = {
        category: sum(1 for keyword in keywords if has_keyword(folded, keyword))
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    best = max(scores, key=lambda category: scores[category])
    return best if scores[best] > 0 else "other"


def extract_problem(title: str, body: str) -> tuple[str, str]:
    """Turn a raw title and body into ``(problem, evidence)``.

    * the problem is the cleaned title, kept as the author wrote it;
    * the evidence is the first sentence of the body that mentions a severity
      word, or the first sentence when none does.

    The function never invents a problem: when the title is empty, the problem
    is empty and the signal is simply less useful (and scored as such).
    """
    problem = clean_title(title)
    sentences = [sentence.strip() for sentence in _SENTENCE_SPLIT.split(body or "")]
    sentences = [sentence for sentence in sentences if len(sentence) > 20]

    for sentence in sentences:
        if severity_hits(sentence):
            return problem, clip(sentence, 300)
    if sentences:
        return problem, clip(sentences[0], 300)
    return problem, ""


_ISSUE_PREFIX = re.compile(
    r"^\s*\[?(fix|bug|regression|error|issue|problem|p[0-9])\]?[\s:()\[]",
    re.IGNORECASE,
)

#: Commit / conventional-commit prefixes: history, not problem reports.
_COMMIT_PREFIX = re.compile(
    r"^(docs|chore|build|ci|test|release|style|refactor|perf|feat|feature|deps|dependabot)\b[:(]",
    re.IGNORECASE,
)

#: Announcement prefixes: launches and marketing, not problems.
_ANNOUNCEMENT_PREFIX = re.compile(
    r"^(introducing|announcing|launching|we (built|made|launched)|meet|presenting|"
    r"new release|release notes)\b",
    re.IGNORECASE,
)

#: Explicit bug markers, checked before the title is cleaned.
_BUG_MARKER = re.compile(r"\[(bug|regression|defect|crash)\]|\((bug|regression)\)", re.IGNORECASE)


def is_problem_like(title: str) -> bool:
    """Heuristic filter: does this *title* describe a problem or a need?

    Only the title is considered, deliberately. Search APIs match the body too,
    so a body-based filter lets "Papers - November 2026" through whenever the
    text mentions "rate limit"; the problem statement would then be a title
    that says nothing. Precision matters more than recall: a radar full of
    launch announcements and changelogs is unusable.
    """
    if not title.strip():
        return False

    # An explicit marker survives the cleaning of the title.
    if _BUG_MARKER.search(title):
        return True

    cleaned = clean_title(title)
    if not cleaned:
        return False
    if _COMMIT_PREFIX.match(cleaned) or _ANNOUNCEMENT_PREFIX.match(cleaned):
        return False
    if "?" in cleaned:
        return True
    if severity_hits(cleaned):
        return True
    if _ISSUE_PREFIX.match(cleaned):
        return True
    return infer_category(cleaned) != "other"


def slug(text: str, limit: int = 60) -> str:
    """Small ASCII slug, used for report anchors and file names."""
    value = re.sub(r"[^a-z0-9]+", "-", fold(text)).strip("-")
    return value[:limit].strip("-") or "cluster"
