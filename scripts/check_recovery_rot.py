#!/usr/bin/env python3
"""Archive-rot recheck — item 2 of almanac-template#11.

`check_links.py` probes each entry's canonical source URL. This script probes
the *other* side of the catalog: every `recovery[]` candidate URL, for every
entry regardless of status. Wayback links die too, community mirrors go
offline, and a `recovery[]` list nobody re-checks is exactly the "monitoring
the monitor" gap this catalog exists to close.

`permission: excluded` candidates are skipped — they are retained for audit
and never surfaced, so their reachability is not this script's concern.

Read-only. Reuses check_links.py's `_probe` (same UA / retry / headless-fallback
logic) so both probes share one bot-defense strategy instead of drifting apart.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_links import _headless_default, _probe, DEFAULT_TIMEOUT  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, metavar="SEC",
                    help=f"per-request timeout in seconds (default: {DEFAULT_TIMEOUT})")
    ap.add_argument("--headless", action=argparse.BooleanOptionalAction,
                    default=_headless_default(),
                    help="verify CDN-bot-blocked candidates with a headless browser "
                         "(defaults to reachability.headless in config)")
    args = ap.parse_args()

    report = []
    rotted = 0
    for path in sorted(CATALOG.glob("*.yaml")):
        entry = yaml.safe_load(path.read_text())
        entry_id = entry.get("id")
        for candidate in entry.get("recovery") or []:
            url = candidate.get("url")
            permission = candidate.get("permission")
            if not url or permission == "excluded":
                continue
            code, note = _probe(url, args.timeout, headless=args.headless)
            blocked = code in {401, 403, 406, 429}
            reachable = code is not None and code < 400
            # Same honesty rule as check_links.py: a bot-defense block is
            # unverifiable, not proof of rot. Only a definitive failure counts.
            rot = (not reachable) and (not blocked)
            if rot:
                rotted += 1
            report.append({
                "id": entry_id, "via": candidate.get("via"), "url": url,
                "authenticity": candidate.get("authenticity"), "permission": permission,
                "http": code, "reachable": reachable, "blocked": blocked,
                "flagged": rot, "note": note,
            })

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for r in report:
            mark = "ROT " if r["flagged"] else ("blok" if r["blocked"] else "ok  ")
            print(f"[{mark}] {r['id']:34} via={r['via']:12} http={r['http']}  {r['note']}")
        print(f"\n{rotted}/{len(report)} recovery candidate(s) rotted")
    return 1 if rotted else 0


if __name__ == "__main__":
    raise SystemExit(main())
