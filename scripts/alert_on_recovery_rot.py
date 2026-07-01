#!/usr/bin/env python3
"""Turn a recovery-rot report into GitHub issues — item 2 of almanac-template#11.

Mirrors `alert_on_dead_links.py`'s reconcile-by-marker design (idempotent,
auto-closing) but for `recovery[]` candidates instead of canonical sources.
Reuses its `GitHub` client rather than re-implementing the API wrapper.

This never touches the YAML — a rotted recovery candidate is a curator
decision (drop it, replace it, or leave it as a dated audit trail), not
something a bot should silently rewrite. It opens/closes an issue; a human
edits `recovery[]`.

Usage:
    python scripts/check_recovery_rot.py --json | python scripts/alert_on_recovery_rot.py
    python scripts/alert_on_recovery_rot.py --report recovery-rot-report.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import timezone, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alert_on_dead_links import GitHub  # noqa: E402

LABELS = {
    "recovery-rot": ("b60205", "A cataloged recovery[] candidate is unreachable."),
    "automated": ("ededed", "Opened automatically by a workflow."),
    "needs-curation": ("0e8a16", "A human should update the affected catalog entry."),
}
MARKER_PREFIX = "almanac-recovery-rot"


def _marker(entry_id: str, url: str) -> str:
    # url is the stable identifier for a candidate — index into recovery[]
    # shifts whenever recovery_bot.py adds/removes entries, url does not.
    return f"<!-- {MARKER_PREFIX}:id={entry_id} url={url} -->"


def _issue_body(r: dict, today: str) -> str:
    return (
        f"{_marker(r['id'], r['url'])}\n\n"
        f"A `recovery[]` candidate for **`{r['id']}`** was unreachable on {today}.\n\n"
        f"- **URL:** {r['url']}\n"
        f"- **via:** {r['via']}  **authenticity:** {r['authenticity']}\n"
        f"- **HTTP:** {r['http']}\n"
        f"- **Probe note:** {r['note']}\n\n"
        "### What to do\n"
        f"Update `catalog/{r['id']}.yaml`:\n"
        "- If a working copy exists elsewhere, replace this candidate or add a new one.\n"
        "- If no replacement exists, either leave it as a dated audit trail or set its "
        "`permission: excluded` (retained but never surfaced — SCHEMA-V2.md rule 4).\n"
        "- If it is a transient blip, no change — this issue auto-closes when the "
        "probe succeeds again.\n\n"
        "_Opened automatically by the recovery-rot check "
        "(`scripts/check_recovery_rot.py`, almanac-template#11 item 2)._"
    )


def reconcile(report: list[dict], gh: GitHub) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    flagged = [r for r in report if r.get("flagged")]
    reachable_now = {(r["id"], r["url"]): r for r in report if r.get("reachable")}

    open_issues = gh.open_automated_issues(label="recovery-rot")
    gh.ensure_labels(LABELS)

    for r in sorted(flagged, key=lambda r: (r["id"], r["url"])):
        marker = _marker(r["id"], r["url"])
        if any(marker in (i.get("body") or "") for i in open_issues):
            print(f"already tracking {r['id']} ({r['url']})")
            continue
        gh.create_issue(
            f"[recovery-rot] {r['id']} candidate unreachable",
            _issue_body(r, today),
            ["recovery-rot", "automated", "needs-curation"],
        )
        print(f"opened issue for {r['id']} ({r['url']})")

    still_flagged = {(r["id"], r["url"]) for r in flagged}
    for issue in open_issues:
        body = issue.get("body") or ""
        tag = f"{MARKER_PREFIX}:id="
        if tag not in body:
            continue
        rest = body.split(tag, 1)[1]
        entry_id = rest.split(" url=", 1)[0].strip()
        url = rest.split(" url=", 1)[1].split(" ", 1)[0].strip()
        key = (entry_id, url)
        if key in reachable_now and key not in still_flagged:
            gh.close_issue(
                issue["number"],
                f"Reachable again as of {today} (HTTP {reachable_now[key]['http']}). "
                "Closing automatically.",
            )
            print(f"closed recovered issue #{issue['number']} ({entry_id})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", help="path to check_recovery_rot.py --json output (default: stdin)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan; do not touch GitHub")
    args = ap.parse_args()

    raw = open(args.report).read() if args.report else sys.stdin.read()
    report = json.loads(raw)
    if not isinstance(report, list):
        raise SystemExit("expected a JSON list from check_recovery_rot.py --json")

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not args.dry_run and not (repo and token):
        raise SystemExit("GITHUB_REPOSITORY and GITHUB_TOKEN are required (or use --dry-run)")

    gh = GitHub(repo, token, args.dry_run)
    reconcile(report, gh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
