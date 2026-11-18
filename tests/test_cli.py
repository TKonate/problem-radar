"""End-to-end tests for the command line interface."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from problem_radar.cli import EXIT_ERROR, EXIT_OK, build_parser
from problem_radar.config import load_config
from problem_radar.sources import HttpClient
from problem_radar.store import load_signals
from tests.helpers import FakeTransport, make_sandbox, run_cli, run_cli_raw


def make_client() -> HttpClient:
    return HttpClient(
        FakeTransport(
            {
                "hn.algolia.com": "file:hn_search_ask.json",
                "api.github.com": "file:github_search_llm.json",
            }
        ),
        min_intervals={},
        sleep=lambda _seconds: None,
    )


class InitTests(unittest.TestCase):
    def test_init_creates_a_working_project(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp:
            code, out, err = run_cli_raw(["init", temp])
            self.assertEqual(code, EXIT_OK, err)
            config_path = Path(temp) / "config" / "radar.json"
            self.assertTrue(config_path.is_file())
            self.assertTrue((Path(temp) / "data").is_dir())
            self.assertTrue((Path(temp) / "reports").is_dir())
            config = load_config(config_path)
            self.assertEqual(config.data_dir, (Path(temp) / "data").resolve())
            self.assertEqual(config.report_dir, (Path(temp) / "reports").resolve())
            self.assertIn("configuration written", out)

    def test_init_refuses_to_overwrite(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp:
            run_cli_raw(["init", temp])
            code, _, err = run_cli_raw(["init", temp])
            self.assertEqual(code, EXIT_ERROR)
            self.assertIn("already exists", err)
            code, _, err = run_cli_raw(["init", temp, "--force"])
            self.assertEqual(code, EXIT_OK, err)


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp, self.sandbox = make_sandbox()
        self.config = self.sandbox.config

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *args: str) -> tuple[int, str, str]:
        return run_cli(list(args), self.sandbox.config_path)

    def populated(self) -> None:
        with patch("problem_radar.pipeline.HttpClient", return_value=make_client()):
            code, out, err = self.cli("collect")
        self.assertEqual(code, EXIT_OK, err + out)
        self.cli("cluster")

    def test_parser_has_commands(self) -> None:
        actions = build_parser()._subparsers._group_actions  # type: ignore[attr-defined]
        names = set(actions[0].choices)  # type: ignore[index]
        for command in (
            "init",
            "collect",
            "cluster",
            "report",
            "run",
            "sources",
            "list",
            "show",
            "status",
            "solution",
            "add",
            "export",
        ):
            self.assertIn(command, names)

    def test_sources(self) -> None:
        code, out, _ = self.cli("sources")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("hackernews", out)
        self.assertIn("3 source(s), 3 enabled", out)

    def test_add_signal(self) -> None:
        code, out, err = self.cli(
            "add",
            "--title",
            "Agent crashes when the tool returns 500",
            "--url",
            "https://example.org/post",
            "--body",
            "It crashes every time.",
            "--domain",
            "ai-agents",
        )
        self.assertEqual(code, EXIT_OK, err)
        self.assertIn("1 signal added", out)
        stored = load_signals(self.config.signals_path)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].domain, "ai-agents")

    def test_add_duplicate(self) -> None:
        args = ("add", "--title", "Agent crashes", "--url", "https://example.org/post")
        self.cli(*args)
        code, out, _ = self.cli(*args)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("0 signal added", out)

    def test_collect_with_fake_transport(self) -> None:
        with patch("problem_radar.pipeline.HttpClient", return_value=make_client()):
            code, out, err = self.cli("collect")
        self.assertEqual(code, EXIT_OK, err)
        self.assertIn("hackernews:", out)
        self.assertTrue(self.config.signals_path.is_file())
        self.assertGreater(len(load_signals(self.config.signals_path)), 0)

    def test_collect_dry_run(self) -> None:
        with patch("problem_radar.pipeline.HttpClient", return_value=make_client()):
            code, out, _ = self.cli("collect", "--dry-run")
        self.assertEqual(code, EXIT_OK)
        self.assertFalse(self.config.signals_path.exists())

    def test_cluster_list_show_status_solution(self) -> None:
        self.populated()

        code, out, _ = self.cli("list")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("cluster(s)", out)
        cluster_id = out.split()[0]

        code, out, _ = self.cli("list", "--json")
        payload = json.loads(out)
        self.assertTrue(payload)
        self.assertIn("score", payload[0])

        code, out, _ = self.cli("show", cluster_id)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Evidence", out)

        code, out, _ = self.cli("status", cluster_id, "researched")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("→ researched", out)

        code, out, _ = self.cli(
            "solution",
            cluster_id,
            "--status",
            "none_found",
            "--note",
            "searched GitHub and HN",
            "--by",
            "tester",
        )
        self.assertEqual(code, EXIT_OK)
        self.assertIn("no solution found", out)

        code, out, _ = self.cli("show", cluster_id)
        self.assertIn("searched GitHub and HN", out)

    def test_status_transition_is_checked(self) -> None:
        self.populated()
        cluster_id = self.cli("list", "--json")[1]
        cluster_id = json.loads(cluster_id)[0]["id"]

        code, _, err = self.cli("status", cluster_id, "deployed")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("cannot move", err)

        code, _, err = self.cli("status", cluster_id, "deployed", "--force")
        self.assertEqual(code, EXIT_OK, err)

    def test_unknown_cluster(self) -> None:
        self.populated()
        code, _, err = self.cli("show", "zzzz")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("no cluster matches", err)

    def test_ambiguous_prefix(self) -> None:
        self.populated()
        code, _, err = self.cli("show", "z")
        self.assertIn(code, (EXIT_OK, EXIT_ERROR))
        if code == EXIT_ERROR:
            self.assertIn("matches", err)

    def test_report(self) -> None:
        self.populated()
        code, out, err = self.cli("report")
        self.assertEqual(code, EXIT_OK, err)
        self.assertIn("report written", out)
        reports = list(self.config.report_dir.glob("*.md"))
        self.assertEqual(len(reports), 1)
        self.assertIn("Problem Radar", reports[0].read_text(encoding="utf-8"))

    def test_report_stdout(self) -> None:
        self.populated()
        code, out, _ = self.cli("report", "--no-write", "--top", "3")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("# Problem Radar", out)

    def test_export(self) -> None:
        self.populated()
        destination = self.sandbox.directory / "export.json"
        code, out, err = self.cli("export", str(destination))
        self.assertEqual(code, EXIT_OK, err)
        self.assertTrue(destination.is_file())
        self.assertIn("exported", out)

    def test_run_end_to_end(self) -> None:
        with patch("problem_radar.pipeline.HttpClient", return_value=make_client()):
            code, out, err = self.cli("run")
        self.assertEqual(code, EXIT_OK, err)
        self.assertIn("new signal(s)", out)
        self.assertIn("report written", out)
        self.assertTrue(self.config.clusters_path.is_file())

    def test_list_filters(self) -> None:
        self.populated()
        code, out, _ = self.cli("list", "--min-score", "99", "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(json.loads(out), [])
        code, out, _ = self.cli("list", "--status", "rejected")
        self.assertIn("No cluster matches", out)

    def test_quiet(self) -> None:
        code, out, _ = self.cli("sources", "-q")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out, "")

    def test_missing_configuration(self) -> None:
        code, _, err = run_cli_raw(["-c", str(self.sandbox.directory / "nope.json"), "sources"])
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("configuration not found", err)

    def test_version_flag(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            build_parser().parse_args(["--version"])
        self.assertEqual(caught.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
