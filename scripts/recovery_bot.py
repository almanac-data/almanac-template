#!/usr/bin/env python3
"""Recovery-candidate discovery bot — item 1 of almanac-template#11.

For every catalog entry whose `status` is `dark` or `superseded`, searches
trusted institutional sources via jeles-remote (a stateless FastAPI proxy onto
Willow's Jeles librarian, https://github.com/rudi193-cmd/jeles-remote) and
proposes `recovery[]` candidates for curator review.

Constitution constraint (SCHEMA-V2.md rule 4, this issue's non-negotiable):
this bot PROPOSES, it never auto-writes a lifecycle or authenticity verdict.
Every candidate it adds gets `authenticity: asserted` (the lowest tier — a
search hit, not a verified match) and `permission: review` (the gate stays
closed until a human looks). It never sets `status`, `status_source`, or a
higher `authenticity`/`permission` tier itself.

Two modes:
  --json           print a report of what would change, make no git changes
  (default)        for each entry with new candidates, open one PR
                    (one dataset = one file = one PR, per CONTRIBUTING.md)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
CONFIG = ROOT / "almanac.config.yml"

RECOVERY_STATUSES = {"dark", "superseded"}
MAX_CANDIDATES_PER_ENTRY = 3
JELES_REMOTE_URL_DEFAULT = "https://jeles-remote.fly.dev/search"


def _config() -> dict:
    if CONFIG.exists():
        return yaml.safe_load(CONFIG.read_text()) or {}
    return {}


def _search(query: str, url: str, secret: str, timeout: float = 60.0) -> dict:
    body = json.dumps({"query": query, "limit_per_source": MAX_CANDIDATES_PER_ENTRY}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "X-Jeles-Secret": secret},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"error": str(exc), "results": {}}


def _existing_urls(entry: dict) -> set[str]:
    return {c.get("url") for c in (entry.get("recovery") or []) if c.get("url")}


def _candidates_from_search(search_result: dict, seen: set[str]) -> list[dict]:
    """Flatten jeles-remote's per-source results into recovery[] candidate dicts."""
    out = []
    for source_hits in (search_result.get("results") or {}).values():
        for hit in source_hits:
            url = hit.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            institution = hit.get("institution") or hit.get("source") or "unknown"
            out.append({
                "via": "jeles-search",
                "url": url,
                "authenticity": "asserted",
                "permission": "review",
                "captured": None,
                "notes": (
                    f"Proposed by recovery_bot.py — jeles-remote search hit "
                    f"({institution}). Not verified against a baseline; curator "
                    f"must confirm authenticity/permission before promoting."
                ),
            })
            if len(out) >= MAX_CANDIDATES_PER_ENTRY:
                return out
    return out


def _query_for(entry: dict) -> str:
    parts = [entry.get("title", ""), entry.get("publisher", "")]
    parts.extend(entry.get("topics") or [])
    return " ".join(p for p in parts if p)


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)


def _pr_exists(branch: str) -> bool:
    proc = _run(["gh", "pr", "list", "--head", branch, "--json", "number"])
    if proc.returncode != 0:
        return False
    try:
        return bool(json.loads(proc.stdout or "[]"))
    except json.JSONDecodeError:
        return False


def _open_pr(entry_id: str, path: Path, added: list[dict], today: str) -> str | None:
    branch = f"recovery-bot/{entry_id}"
    _run(["git", "fetch", "origin", branch])
    if _pr_exists(branch):
        return None  # already proposed; don't spam a second PR for the same entry

    _run(["git", "checkout", "-B", branch, "origin/main"])
    _run(["git", "add", str(path.relative_to(ROOT))])
    commit = _run([
        "git", "commit", "-m",
        f"propose(recovery): {len(added)} candidate(s) for {entry_id}",
        "-m", "Opened by scripts/recovery_bot.py — review before merging. "
              "Never merges/promotes automatically.",
    ])
    if commit.returncode != 0:
        return None  # nothing to commit (e.g. all candidates already present)

    push = _run(["git", "push", "-u", "origin", branch, "--force-with-lease"])
    if push.returncode != 0:
        print(f"  push failed for {branch}: {push.stderr.strip()}", file=sys.stderr)
        return None

    body = (
        f"Recovery candidates proposed for `{entry_id}` from a jeles-remote search "
        f"on {today}.\n\n"
        + "\n".join(f"- {c['via']}: {c['url']}" for c in added)
        + "\n\n**Every candidate is `authenticity: asserted` / `permission: review`** — "
          "this is a search hit, not a verified match. A curator must confirm "
          "authenticity and flip `permission` before it's actionable "
          "(SCHEMA-V2.md rules 2/4).\n\n"
          "_Opened automatically by `scripts/recovery_bot.py` "
          "(almanac-template#11, item 1)._"
    )
    create = _run([
        "gh", "pr", "create",
        "--title", f"propose(recovery): candidates for {entry_id}",
        "--body", body,
    ])
    if create.returncode != 0:
        print(f"  pr create failed for {branch}: {create.stderr.strip()}", file=sys.stderr)
        return None
    return create.stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="report only, no git/PR side effects")
    ap.add_argument("--jeles-remote-url", default=None,
                     help=f"override endpoint (default: {JELES_REMOTE_URL_DEFAULT} or "
                          "$JELES_REMOTE_URL)")
    args = ap.parse_args()

    import os
    url = args.jeles_remote_url or os.environ.get("JELES_REMOTE_URL", JELES_REMOTE_URL_DEFAULT)
    secret = os.environ.get("JELES_REMOTE_SECRET", "")
    if not secret:
        print("JELES_REMOTE_SECRET not set — nothing to do", file=sys.stderr)
        return 1

    import datetime
    today = datetime.date.today().isoformat()

    start_ref = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()

    report = []
    for path in sorted(CATALOG.glob("*.yaml")):
        entry = yaml.safe_load(path.read_text())
        if entry.get("status") not in RECOVERY_STATUSES:
            continue

        seen = _existing_urls(entry)
        result = _search(_query_for(entry), url, secret)
        candidates = _candidates_from_search(result, seen)

        report.append({
            "id": entry.get("id"), "status": entry.get("status"),
            "new_candidates": len(candidates), "error": result.get("error"),
        })
        if not candidates:
            continue

        entry.setdefault("recovery", []).extend(candidates)

        if args.json:
            continue

        path.write_text(yaml.safe_dump(entry, sort_keys=False, default_flow_style=False,
                                        allow_unicode=True))
        pr_url = _open_pr(entry["id"], path, candidates, today)
        if pr_url:
            print(f"opened {pr_url}")
        # restore the working tree to where we started before the next entry
        _run(["git", "checkout", start_ref])

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        proposed = sum(1 for r in report if r["new_candidates"])
        print(f"{proposed}/{len(report)} dark/superseded entr{'y' if len(report)==1 else 'ies'} "
              "got new recovery candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
