"""Command line interface.

Design rules (same as the rest of the tool): small functions per subcommand,
readable errors with exit codes, and no hidden network call. ``collect`` is the
only command that touches the internet and it says so. The CLI never prompts
and never edits the configuration: every input comes from argv or the config
file, which is what keeps it usable from cron.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .config import Config, load_config, write_default_config
from .errors import RadarError, ValidationError
from .models import (
    PIPELINE_STATUSES,
    SOLUTION_STATUSES,
    Cluster,
    Signal,
    Solution,
    utc_now,
)
from .pipeline import collect, load_or_rebuild, rebuild_clusters
from .report import RECOMMENDATIONS, STATUS_LABELS, export_json, render_cluster, write_report
from .scoring import DEFAULT_THRESHOLDS
from .store import append_signals, load_clusters, load_signals, save_clusters
from .taxonomy import CATEGORIES, DOMAINS
from .text import extract_problem, infer_category, infer_domain

EXIT_OK = 0
EXIT_ERROR = 1

#: Allowed pipeline transitions (``rejected`` can be reopened).
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "discovered": {"clustered", "rejected"},
    "clustered": {"researched", "rejected"},
    "researched": {"proposed", "rejected"},
    "proposed": {"approved", "rejected"},
    "approved": {"built", "rejected"},
    "built": {"deployed", "rejected"},
    "deployed": set(),
    "rejected": {"clustered"},
}

EXAMPLES = """\
examples:
  radar init .                       # config/radar.json + data/
  radar collect                      # public APIs only
  radar run                          # collect + cluster + score + report
  radar list --min-score 40
  radar show 3f2a9c
  radar solution 3f2a9c --status none_found --note "searched GitHub, HN, PyPI"
  radar status 3f2a9c researched
  radar report --top 10
"""


def _add_config_option(parser: argparse.ArgumentParser) -> None:
    """Add ``--config`` and ``--quiet`` to a parser or a subcommand.

    Both options default to ``argparse.SUPPRESS`` so a subparser does not
    overwrite the value parsed by the top-level parser with its own default.
    """
    parser.add_argument(
        "-c",
        "--config",
        metavar="PATH",
        default=argparse.SUPPRESS,
        help="configuration file (default: config/radar.json)",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", default=argparse.SUPPRESS, help="only print errors"
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    common = argparse.ArgumentParser(add_help=False)
    _add_config_option(common)

    parser = argparse.ArgumentParser(
        prog="radar",
        description="Problem Radar — collect public problems, cluster them, score opportunities.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_config_option(parser)
    parser.add_argument("-V", "--version", action="version", version=f"problem-radar {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    init = subparsers.add_parser(
        "init", parents=[common], help="create a configuration and the data directory"
    )
    init.add_argument("path", nargs="?", default=".", help="project directory (default: .)")
    init.add_argument("--force", action="store_true", help="overwrite an existing configuration")

    collect_parser = subparsers.add_parser(
        "collect", aliases=["c"], parents=[common], help="collect signals from public sources"
    )
    collect_parser.add_argument("--source", help="run a single configured source")
    collect_parser.add_argument("--limit", type=int, help="items per query/feed")
    collect_parser.add_argument("--dry-run", action="store_true", help="do not write anything")

    subparsers.add_parser(
        "cluster", aliases=["cl"], parents=[common], help="re-cluster and re-score stored signals"
    )

    report_parser = subparsers.add_parser(
        "report", aliases=["r"], parents=[common], help="write the Markdown report"
    )
    report_parser.add_argument("--top", type=int, help="number of detailed clusters")
    report_parser.add_argument("--output", metavar="PATH", help="report path")
    report_parser.add_argument("--json", metavar="PATH", help="also export the data as JSON")
    report_parser.add_argument("--no-write", action="store_true", help="print instead of writing")

    run_parser = subparsers.add_parser(
        "run", parents=[common], help="collect, cluster, score and report in one go"
    )
    run_parser.add_argument("--limit", type=int, help="items per query/feed")
    run_parser.add_argument("--top", type=int, help="number of detailed clusters")
    run_parser.add_argument("--json", metavar="PATH", help="also export the data as JSON")

    subparsers.add_parser("sources", parents=[common], help="list configured sources")

    list_parser = subparsers.add_parser(
        "list", aliases=["ls"], parents=[common], help="list clusters"
    )
    list_parser.add_argument("--status", choices=PIPELINE_STATUSES)
    list_parser.add_argument("--recommendation", choices=sorted(RECOMMENDATIONS))
    list_parser.add_argument("--min-score", type=float, default=0.0)
    list_parser.add_argument("--json", action="store_true")

    show_parser = subparsers.add_parser(
        "show", parents=[common], help="show one cluster and its evidence"
    )
    show_parser.add_argument("cluster_id")
    show_parser.add_argument("--json", action="store_true")

    status_parser = subparsers.add_parser(
        "status", parents=[common], help="move a cluster through the pipeline"
    )
    status_parser.add_argument("cluster_id")
    status_parser.add_argument("status", choices=PIPELINE_STATUSES)
    status_parser.add_argument("--note", help="replace the cluster note")
    status_parser.add_argument("--force", action="store_true", help="skip transition validation")

    solution_parser = subparsers.add_parser(
        "solution", parents=[common], help="record a solution search result"
    )
    solution_parser.add_argument("cluster_id")
    solution_parser.add_argument("--status", required=True, choices=SOLUTION_STATUSES)
    solution_parser.add_argument("--url", default="")
    solution_parser.add_argument("--note", default="")
    solution_parser.add_argument("--by", default="human", help="who did the search")

    add_parser = subparsers.add_parser(
        "add", parents=[common], help="add a manual signal (no network)"
    )
    add_parser.add_argument("--title", required=True)
    add_parser.add_argument("--url", required=True)
    add_parser.add_argument("--body", default="")
    add_parser.add_argument("--author", default="")
    add_parser.add_argument("--date", dest="published_at", default="")
    add_parser.add_argument("--domain", choices=DOMAINS)
    add_parser.add_argument("--category", choices=CATEGORIES)

    export_parser = subparsers.add_parser(
        "export", parents=[common], help="export clusters and signals as JSON"
    )
    export_parser.add_argument("path", help="destination JSON file")

    return parser


def _out(args: argparse.Namespace, message: str = "") -> None:
    """Print to stdout unless ``--quiet`` was given.

    Errors deliberately bypass this helper and always go to stderr, so
    ``--quiet`` can never hide a failure.
    """
    if not getattr(args, "quiet", False):
        print(message)


def _load(args: argparse.Namespace) -> Config:
    """Load the configuration and make sure the output directories exist.

    Directory creation happens here on purpose: every command may write, and
    none should have to check for the directories first.
    """
    config = load_config(getattr(args, "config", None) or "config/radar.json")
    config.ensure_directories()
    return config


def _find_cluster(clusters: list[Cluster], prefix: str) -> Cluster:
    """Find a cluster by exact id or unambiguous prefix."""
    matches = [cluster for cluster in clusters if cluster.id == prefix]
    if not matches:
        matches = [cluster for cluster in clusters if cluster.id.startswith(prefix)]
    if not matches:
        raise ValidationError(
            f"no cluster matches {prefix!r}",
            ["run 'radar list' to see the available ids"],
        )
    if len(matches) > 1:
        raise ValidationError(
            f"{prefix!r} matches {len(matches)} clusters",
            [cluster.id for cluster in matches[:10]],
        )
    return matches[0]


def cmd_init(args: argparse.Namespace) -> int:
    """Create a ready-to-run project directory."""
    target = Path(args.path).expanduser().resolve()
    config_path = target / "config" / "radar.json"
    if config_path.exists() and not args.force:
        print(f"configuration already exists: {config_path}", file=sys.stderr)
        return EXIT_ERROR

    target.mkdir(parents=True, exist_ok=True)
    for directory in ("data", "reports"):
        (target / directory).mkdir(exist_ok=True)
    written = write_default_config(target)
    print(f"configuration written: {written}")
    print(f"data directory: {target / 'data'}")
    print("next: radar collect && radar report")
    return EXIT_OK


def cmd_sources(args: argparse.Namespace) -> int:
    """List the configured sources and their reliability tier."""
    config = _load(args)
    rows = []
    for source in config.sources:
        state = "on " if source.enabled else "off"
        queries = len(source.queries) or len(source.feeds) or 1
        rows.append((state, source.name, source.kind, source.tier, str(queries), str(source.limit)))
    widths = [max(len(row[index]) for row in rows) for index in range(5)]
    for row in rows:
        _out(
            args,
            "  ".join(row[index].ljust(widths[index]) for index in range(5)) + f"  {row[5]}",
        )
    _out(args, f"\n{len(config.sources)} source(s), {len(config.enabled_sources)} enabled.")
    return EXIT_OK


def cmd_collect(args: argparse.Namespace) -> int:
    """Run the collectors."""
    config = _load(args)
    summary = collect(config, only=args.source, limit=args.limit, dry_run=args.dry_run)

    for report in summary.sources:
        _out(
            args,
            f"{report.name}: {report.added} new, {report.skipped} already known, "
            f"{report.filtered} filtered out of {report.collected}",
        )
        for error in report.errors:
            print(f"  warning: {error}", file=sys.stderr)

    _out(args, f"\n{summary.total_added} new signal(s) stored in {config.signals_path}.")
    return EXIT_OK if not summary.errors else EXIT_ERROR


def cmd_cluster(args: argparse.Namespace) -> int:
    """Re-cluster and re-score the stored signals."""
    config = _load(args)
    clusters = rebuild_clusters(config)
    _out(args, f"{len(clusters)} cluster(s) written to {config.clusters_path}.")
    return EXIT_OK


def cmd_report(args: argparse.Namespace) -> int:
    """Print or write the Markdown report, and optionally the JSON export."""
    config = _load(args)
    clusters = load_or_rebuild(config)
    signals = load_signals(config.signals_path)
    top = args.top or config.report_top

    if args.no_write:
        from .report import render_markdown

        print(render_markdown(clusters, signals, config=config, top=top))
    else:
        path = write_report(
            clusters,
            signals,
            config=config,
            top=top,
            output=Path(args.output).expanduser() if args.output else None,
        )
        _out(args, f"report written: {path}")

    if args.json:
        path = export_json(clusters, signals, config=config, output=Path(args.json).expanduser())
        _out(args, f"data exported: {path}")
    return EXIT_OK


def cmd_run(args: argparse.Namespace) -> int:
    """Collect, cluster and report in one command (cron friendly)."""
    config = _load(args)
    summary = collect(config, limit=args.limit)
    for report in summary.sources:
        _out(
            args,
            f"{report.name}: {report.added} new, {report.filtered} filtered "
            f"out of {report.collected}",
        )
        for error in report.errors:
            print(f"  warning: {error}", file=sys.stderr)

    clusters = rebuild_clusters(config)
    signals = load_signals(config.signals_path)
    top = args.top or config.report_top
    path = write_report(clusters, signals, config=config, top=top)
    _out(args, f"\n{summary.total_added} new signal(s), {len(clusters)} cluster(s).")
    _out(args, f"report written: {path}")
    if args.json:
        exported = export_json(
            clusters, signals, config=config, output=Path(args.json).expanduser()
        )
        _out(args, f"data exported: {exported}")
    return EXIT_OK


def cmd_list(args: argparse.Namespace) -> int:
    """List clusters with filters."""
    config = _load(args)
    clusters = load_or_rebuild(config)
    if args.status:
        clusters = [cluster for cluster in clusters if cluster.status == args.status]
    if args.recommendation:
        clusters = [
            cluster
            for cluster in clusters
            if cluster.score and cluster.score.recommendation == args.recommendation
        ]
    clusters = [
        cluster
        for cluster in clusters
        if (cluster.score.total if cluster.score else 0) >= args.min_score
    ]

    if args.json:
        print(json.dumps([cluster.to_dict() for cluster in clusters], indent=2, ensure_ascii=False))
        return EXIT_OK

    if not clusters:
        _out(args, "No cluster matches.")
        return EXIT_OK

    for cluster in clusters:
        score = f"{cluster.score.total:5.1f}" if cluster.score else "  —  "
        recommendation = cluster.score.recommendation if cluster.score else "-"
        _out(
            args,
            f"{cluster.id}  {score}  {recommendation:<8} {cluster.status:<10} "
            f"{len(cluster.signal_ids):2}  {cluster.title[:70]}",
        )
    _out(args, f"\n{len(clusters)} cluster(s).")
    return EXIT_OK


def cmd_show(args: argparse.Namespace) -> int:
    """Show one cluster with its score breakdown and evidence."""
    config = _load(args)
    clusters = load_or_rebuild(config)
    cluster = _find_cluster(clusters, args.cluster_id)
    signals = {signal.id: signal for signal in load_signals(config.signals_path)}

    if args.json:
        print(json.dumps(cluster.to_dict(), indent=2, ensure_ascii=False))
        return EXIT_OK

    print(render_cluster(cluster, signals))
    return EXIT_OK


def cmd_status(args: argparse.Namespace) -> int:
    """Move a cluster through the pipeline."""
    config = _load(args)
    clusters = load_clusters(config.clusters_path)
    if not clusters:
        raise ValidationError("no cluster stored yet", ["run 'radar cluster' first"])

    cluster = _find_cluster(clusters, args.cluster_id)
    current, target = cluster.status, args.status
    if (
        target != current
        and not args.force
        and target not in ALLOWED_TRANSITIONS.get(current, set())
    ):
        allowed = ", ".join(sorted(ALLOWED_TRANSITIONS.get(current, set()))) or "(none)"
        raise ValidationError(
            f"cannot move {cluster.id} from {current!r} to {target!r}",
            [f"allowed from {current!r}: {allowed}", "use --force to override"],
        )

    cluster.status = target
    if args.note is not None:
        cluster.note = args.note
    save_clusters(config.clusters_path, clusters)
    _out(args, f"{cluster.id}: {current} → {target}")
    return EXIT_OK


def cmd_solution(args: argparse.Namespace) -> int:
    """Record what a solution search concluded."""
    config = _load(args)
    clusters = load_clusters(config.clusters_path)
    cluster = _find_cluster(clusters, args.cluster_id)
    solution = Solution(
        status=args.status,
        url=args.url,
        note=args.note,
        checked_at=date.today().isoformat(),
        checked_by=args.by,
    )
    cluster.solutions.append(solution)
    if cluster.status in {"discovered", "clustered"}:
        cluster.status = "researched"
    elif cluster.status == "researched":
        pass
    save_clusters(config.clusters_path, clusters)
    _out(args, f"{cluster.id}: solution recorded ({solution.label}), status {cluster.status}")
    return EXIT_OK


def cmd_add(args: argparse.Namespace) -> int:
    """Add a hand-written signal from the command line."""
    config = _load(args)
    problem, evidence = extract_problem(args.title, args.body)
    combined = f"{args.title} {args.body}"
    signal = Signal(
        source="manual",
        source_id=args.url,
        url=args.url,
        title=args.title,
        body=args.body,
        author=args.author,
        published_at=args.published_at,
        domain=args.domain or infer_domain(combined),
        category=args.category or infer_category(combined),
        problem=problem,
        evidence=evidence,
        confidence=0.5,
        tags=["manual"],
        collected_at=utc_now(),
    )
    added, skipped = append_signals(config.signals_path, [signal])
    _out(args, f"{added} signal added ({skipped} duplicate).")
    return EXIT_OK


def cmd_export(args: argparse.Namespace) -> int:
    """Export clusters and signals to one JSON document."""
    config = _load(args)
    clusters = load_or_rebuild(config)
    path = export_json(
        clusters,
        load_signals(config.signals_path),
        config=config,
        output=Path(args.path).expanduser(),
    )
    _out(args, f"data exported: {path}")
    return EXIT_OK


HANDLERS = {
    "init": cmd_init,
    "collect": cmd_collect,
    "cluster": cmd_cluster,
    "report": cmd_report,
    "run": cmd_run,
    "sources": cmd_sources,
    "list": cmd_list,
    "show": cmd_show,
    "status": cmd_status,
    "solution": cmd_solution,
    "add": cmd_add,
    "export": cmd_export,
}

ALIASES = {"c": "collect", "cl": "cluster", "r": "report", "ls": "list"}


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv``, dispatch the subcommand and return the exit code.

    ``init`` is handled before the handler table because it is the only command
    that works without a configuration file. Expected failures become a message
    on stderr and exit code 1; anything else propagates.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    command = ALIASES.get(args.command or "", args.command)

    try:
        if command == "init":
            return cmd_init(args)
        if command is None:
            parser.print_help()
            return EXIT_OK
        return HANDLERS[command](args)
    except ValidationError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        for detail in exc.details:
            print(f"  - {detail}", file=sys.stderr)
        return EXIT_ERROR
    except RadarError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except BrokenPipeError:  # pragma: no cover - `radar list | head`
        # The reader closed the pipe; exit quietly like any well-behaved CLI.
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0
    except KeyboardInterrupt:  # pragma: no cover - user interruption
        print("\ninterrupted", file=sys.stderr)
        return 130


__all__ = [
    "ALLOWED_TRANSITIONS",
    "DEFAULT_THRESHOLDS",
    "EXIT_ERROR",
    "EXIT_OK",
    "STATUS_LABELS",
    "build_parser",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
