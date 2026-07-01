#!/usr/bin/env python3
"""Turn a revision-drift report into a proposal issue — item 3 of almanac-template#11.

Mirrors `alert_on_dead_links.py` / `alert_on_recovery_rot.py`'s idempotent-marker
design and reuses their `GitHub` client. This never writes `status`,
`status_since`, or `status_source` — per SCHEMA-V2.md's leaning on open item #5,
a reclassification is always a PROPOSAL for curator confirmation, keyed on the
machine facts (`fingerprint_result`, `lead_result`) recorded in the report, not
asserted directly.

Usage:
    python scripts/check_revision_drift.py --json | python scripts/alert_on_revision_drift.py
    python scripts/alert_on_revision_drift.py --report revision-drift-report.json --dry-run
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
    "revision-proposed": ("5319e7", "A machine-observed content drift suggests a status reclassification."),
    "automated": ("ededed", "Opened automatically by a workflow."),
    "needs-curation": ("0e8a16", "A human should update the affected catalog entry."),
}
MARKER_PREFIX = "almanac-revision-proposed"


def _marker(entry_id: str) -> str:
    return f"<!-- {MARKER_PREFIX}:id={entry_id} -->"


def _issue_body(r: dict, today: str) -> str:
    return (
        f"{_marker(r['id'])}\n\n"
        f"A content-drift probe on {today} suggests `{r['id']}` may need reclassifying "
        f"from **`{r['declared_status']}`** to **`{r['proposed_status']}`**.\n\n"
        f"- **URL:** {r['url']}\n"
        f"- **Final URL:** {r.get('final_url', r['url'])}\n"
        f"- **fingerprint_result:** {r['fingerprint_result']}\n"
        f"- **lead_result:** {r['lead_result']}\n\n"
        "### Why this suggestion\n"
        + {
            "revised": "Same URL, but the full-artifact hash no longer matches the captured "
                       "baseline — the content at this URL has changed in place.",
            "moved": "The page redirected, and either the full hash still matches the baseline "
                     "or the lead signature (title + lead text) still matches — strong evidence "
                     "this is the same resource, relocated.",
            "superseded": "The page redirected AND the lead signature (title + lead text) no "
                          "longer matches the baseline — the URL now serves what looks like a "
                          "different resource.",
            "redirected": "The page redirected and the content drifted, but no `lead_hash` "
                          "baseline exists to confirm equivalence — the honest default when "
                          "equivalence can't be verified.",
        }.get(r["proposed_status"], "See the machine facts above.")
        + "\n\n### What to do\n"
        f"Verify manually, then update `catalog/{r['id']}.yaml`:\n"
        f"- If this looks right, set `status: {r['proposed_status']}`, `status_since` to today, "
        "and `status_source: curator`.\n"
        "- If this is a false positive (e.g. the site restructured without changing meaning), "
        "no change — this issue auto-closes when the probe stops flagging it.\n"
        "- Consider updating `fingerprint` to a fresh baseline if you confirm the new content "
        "is now the entry's live truth.\n\n"
        "_Opened automatically by the revision-drift check "
        "(`scripts/check_revision_drift.py`, almanac-template#11 item 3). "
        "This never edits the YAML directly — every reclassification is a proposal._"
    )


def reconcile(report: list[dict], gh: GitHub) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    flagged = [r for r in report if r.get("flagged")]
    still_flagged_ids = {r["id"] for r in flagged}
    open_issues = gh.open_automated_issues(label="revision-proposed")
    gh.ensure_labels(LABELS)

    for r in sorted(flagged, key=lambda r: r["id"]):
        marker = _marker(r["id"])
        existing = next((i for i in open_issues if marker in (i.get("body") or "")), None)
        body = _issue_body(r, today)
        if existing:
            gh.update_issue_body(existing["number"], body)
            print(f"refreshed proposal #{existing['number']} for {r['id']}")
            continue
        gh.create_issue(
            f"[revision-proposed] {r['id']}: {r['declared_status']} -> {r['proposed_status']}?",
            body,
            ["revision-proposed", "automated", "needs-curation"],
        )
        print(f"opened proposal for {r['id']}")

    for issue in open_issues:
        body = issue.get("body") or ""
        tag = f"{MARKER_PREFIX}:id="
        if tag not in body:
            continue
        entry_id = body.split(tag, 1)[1].split(" ", 1)[0].strip()
        if entry_id not in still_flagged_ids:
            gh.close_issue(
                issue["number"],
                f"No longer flagged as of {today} (either curator updated the entry, or the "
                "drift resolved). Closing automatically.",
            )
            print(f"closed resolved proposal #{issue['number']} ({entry_id})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", help="path to check_revision_drift.py --json output (default: stdin)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; do not touch GitHub")
    args = ap.parse_args()

    raw = open(args.report).read() if args.report else sys.stdin.read()
    report = json.loads(raw)
    if not isinstance(report, list):
        raise SystemExit("expected a JSON list from check_revision_drift.py --json")

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not args.dry_run and not (repo and token):
        raise SystemExit("GITHUB_REPOSITORY and GITHUB_TOKEN are required (or use --dry-run)")

    gh = GitHub(repo, token, args.dry_run)
    reconcile(report, gh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
