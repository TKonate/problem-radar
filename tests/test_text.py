"""Tests for :mod:`problem_radar.text`."""

from __future__ import annotations

import unittest

from problem_radar.text import (
    clean_title,
    clip,
    containment,
    extract_problem,
    first_sentence,
    fold,
    infer_category,
    infer_domain,
    is_problem_like,
    jaccard,
    severity_hits,
    similarity,
    slug,
    tokens,
)


class FoldTests(unittest.TestCase):
    def test_accents_and_case(self) -> None:
        self.assertEqual(fold("Souverainetés Fragmentées"), "souverainetes fragmentees")

    def test_clip(self) -> None:
        self.assertEqual(clip("short", 20), "short")
        clipped = clip("a" * 30 + " word", 20)
        self.assertLessEqual(len(clipped), 21)
        self.assertTrue(clipped.endswith("…"))


class TokenTests(unittest.TestCase):
    def test_drops_stopwords(self) -> None:
        self.assertEqual(tokens("the agent is in the loop"), {"agent", "loop"})

    def test_keeps_short_domain_words(self) -> None:
        self.assertIn("ai", tokens("AI and db and ui and os"))

    def test_drops_numbers(self) -> None:
        self.assertNotIn("1234", tokens("issue 1234 crash"))

    def test_empty(self) -> None:
        self.assertEqual(tokens(""), set())


class TitleTests(unittest.TestCase):
    def test_removes_aggregator_prefix(self) -> None:
        self.assertEqual(clean_title("Show HN: My tool"), "My tool")
        self.assertEqual(clean_title("[Bug] It crashes"), "It crashes")
        self.assertEqual(clean_title("  spaced   title  "), "spaced title")

    def test_keeps_normal_title(self) -> None:
        self.assertEqual(clean_title("Why is Docker slow?"), "Why is Docker slow?")


class SimilarityTests(unittest.TestCase):
    def test_jaccard(self) -> None:
        self.assertEqual(jaccard({"a", "b"}, {"a", "b"}), 1.0)
        self.assertEqual(jaccard({"a"}, {"b"}), 0.0)
        self.assertAlmostEqual(jaccard({"a", "b"}, {"b", "c"}), 1 / 3)

    def test_containment(self) -> None:
        self.assertEqual(containment({"a", "b"}, {"a", "b", "c"}), 1.0)
        self.assertEqual(containment(set(), {"a"}), 0.0)

    def test_identical_texts(self) -> None:
        self.assertEqual(similarity("Docker build fails", "Docker build fails"), 1.0)

    def test_similar_texts(self) -> None:
        score = similarity(
            "Postgres connection pool exhausted in production",
            "Postgres connection pool keeps getting exhausted in production",
        )
        self.assertGreater(score, 0.6)

    def test_unrelated_texts(self) -> None:
        score = similarity("Docker build fails", "Why is my calendar not syncing")
        self.assertLess(score, 0.2)


class ExtractionTests(unittest.TestCase):
    def test_first_sentence(self) -> None:
        text = "The build fails every time. Then it crashes at startup."
        self.assertEqual(first_sentence(text), "The build fails every time.")
        self.assertEqual(first_sentence("short"), "short")

    def test_severity_hits(self) -> None:
        self.assertIn("data loss", severity_hits("this causes DATA LOSS"))
        self.assertEqual(severity_hits("nice weather"), set())

    def test_extract_problem_prefers_severity_sentence(self) -> None:
        problem, evidence = extract_problem(
            "Agent loop never stops",
            "I tried the new release. It causes a crash after two minutes of use.",
        )
        self.assertEqual(problem, "Agent loop never stops")
        self.assertIn("crash", evidence)

    def test_extract_problem_falls_back_to_first_sentence(self) -> None:
        _, evidence = extract_problem("A title", "A perfectly calm sentence about nothing.")
        self.assertIn("perfectly calm", evidence)

    def test_extract_problem_without_body(self) -> None:
        problem, evidence = extract_problem("Only a title here", "")
        self.assertEqual(problem, "Only a title here")
        self.assertEqual(evidence, "")

    def test_is_problem_like(self) -> None:
        self.assertTrue(is_problem_like("Why does the agent loop forever?"))
        self.assertTrue(is_problem_like("Data loss when syncing notes"))
        self.assertTrue(is_problem_like("Docs are missing for the CLI"))
        self.assertFalse(is_problem_like("Show HN: my new startup"))
        self.assertFalse(is_problem_like(""))


class InferenceTests(unittest.TestCase):
    def test_domain(self) -> None:
        self.assertEqual(infer_domain("The LLM agent keeps calling tools"), "ai-agents")
        self.assertEqual(infer_domain("Docker volume backup fails"), "data-infra")
        self.assertEqual(infer_domain("CVE in the auth library"), "security")
        self.assertEqual(infer_domain("nice weather"), "other")

    def test_category(self) -> None:
        self.assertEqual(infer_category("App crashes with a panic"), "recurring-bug")
        self.assertEqual(infer_category("No way to export to CSV"), "missing-feature")
        self.assertEqual(infer_category("Pricing is too expensive for a hobby"), "cost")
        self.assertEqual(infer_category("nice weather"), "other")


class SlugTests(unittest.TestCase):
    def test_slug(self) -> None:
        self.assertEqual(slug("Agent loop never stops!"), "agent-loop-never-stops")
        self.assertEqual(slug("###"), "cluster")
        self.assertEqual(len(slug("x " * 80, limit=10)), 9)


if __name__ == "__main__":
    unittest.main()
