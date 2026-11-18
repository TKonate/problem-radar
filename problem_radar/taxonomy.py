"""Taxonomy: domains, categories and source reliability.

The taxonomy is intentionally small. Its job is to keep the report readable and
to let the scoring reward diversity, not to be an ontology. Every keyword list is
data, not logic, so it can be extended from ``config.json`` without touching the
code (see :func:`problem_radar.config.load_config`).
"""

from __future__ import annotations

#: Domains of the MVP scope (AI, agents, developer tools).
DOMAINS: tuple[str, ...] = (
    "ai-agents",
    "dev-tools",
    "data-infra",
    "security",
    "productivity",
    "other",
)

#: What kind of friction the signal describes.
CATEGORIES: tuple[str, ...] = (
    "recurring-bug",
    "missing-feature",
    "integration-pain",
    "docs-gap",
    "cost",
    "performance",
    "ux-friction",
    "maintenance",
    "other",
)

#: Keywords used to infer a domain from free text.
DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ai-agents": (
        "llm",
        "agent",
        "prompt",
        "rag",
        "embedding",
        "openai",
        "anthropic",
        "ollama",
        "model",
        "inference",
        "token",
        "mcp",
        "langchain",
        "vector",
        "fine-tune",
    ),
    "dev-tools": (
        "cli",
        "editor",
        "vscode",
        "neovim",
        "git",
        "debug",
        "compiler",
        "linter",
        "test",
        "refactor",
        "ide",
        "package",
        "dependency",
        "build",
    ),
    "data-infra": (
        "database",
        "postgres",
        "sqlite",
        "docker",
        "kubernetes",
        "backup",
        "storage",
        "pipeline",
        "etl",
        "queue",
        "cache",
        "server",
        "deploy",
    ),
    "security": (
        "security",
        "vulnerability",
        "cve",
        "exploit",
        "auth",
        "token leak",
        "secret",
        "encryption",
        "phishing",
        "malware",
        "permission",
    ),
    "productivity": (
        "obsidian",
        "notion",
        "calendar",
        "task",
        "notes",
        "workflow",
        "automation",
        "email",
        "sync",
        "export",
    ),
}

#: Keywords used to infer a category from free text.
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "recurring-bug": (
        "crash",
        "crashes",
        "broken",
        "regression",
        "bug",
        "fails",
        "failing",
        "panic",
        "exception",
        "corrupt",
        "data loss",
        "freeze",
        "hang",
        "memory leak",
    ),
    "missing-feature": (
        "feature request",
        "would be nice",
        "no way to",
        "cannot",
        "can't",
        "support for",
        "missing",
        "add support",
    ),
    "integration-pain": (
        "integration",
        "integrate",
        "webhook",
        "api",
        "sdk",
        "plugin",
        "extension",
        "compatible",
        "sync between",
        "import from",
        "export to",
    ),
    "docs-gap": (
        "documentation",
        "docs",
        "undocumented",
        "no example",
        "unclear",
        "tutorial",
        "guide",
        "readme",
    ),
    "cost": (
        "expensive",
        "pricing",
        "cost",
        "billing",
        "quota",
        "rate limit",
        "cheaper",
        "price",
        "paywall",
    ),
    "performance": (
        "slow",
        "latency",
        "timeout",
        "performance",
        "takes forever",
        "oom",
        "cpu",
        "memory",
        "throughput",
        "benchmark",
    ),
    "ux-friction": (
        "confusing",
        "annoying",
        "hard to",
        "tedious",
        "manual",
        "friction",
        "ux",
        "interface",
        "unusable",
    ),
    "maintenance": (
        "abandoned",
        "unmaintained",
        "stale",
        "no release",
        "last commit",
        "deprecated",
        "fork",
        "maintainer",
    ),
}

#: Reliability of a source family, and the confidence it gives a signal.
#: These numbers are a judgement, documented in ``docs/methodology.md``.
SOURCE_TIERS: dict[str, float] = {
    "official": 0.95,  # vendor issue tracker, changelog, release notes
    "issue-tracker": 0.85,  # public bug tracker of a project
    "community": 0.60,  # forum, Q&A, mailing list archive
    "blog": 0.55,  # technical blog post
    "social": 0.35,  # aggregator, social network
    "unknown": 0.25,
}

#: Words that signal severity when they appear in a title or body.
SEVERITY_WORDS: tuple[str, ...] = (
    "data loss",
    "corrupt",
    "crash",
    "crashes",
    "security",
    "vulnerability",
    "leak",
    "regression",
    "broken",
    "urgent",
    "blocked",
    "cannot",
    "can't",
    "fails",
    "failed",
    "panic",
    "outage",
    "downtime",
    "lost",
    "not found",
    "not working",
    "doesn't work",
    "does not work",
    "unable",
    "error",
    "missing",
    "unsupported",
    "invalid",
    "timeout",
    "timed out",
    "exceeded",
)

#: Filler words removed before similarity comparison.
STOPWORDS: frozenset[str] = frozenset(
    """
    a an and are as at be been but by can could do does did for from had has have how
    i if in into is it its just like make me more most my no not of on or our so some
    than that the their them then there these they this to too up us use used using
    very was we were what when where which who why will with without would you your
    about after all also any because before being between both each even ever every
    few get got had has have he her here him his if in into it its just may me might
    much must my no nor not now of off on once only or other our out over own same
    she should since so some still such than that the their them then there these
    they this those through to too under until up very was we were what when where
    which while who whom why will with within without would you your
    ask hn show hn launch
    """.split()
)
