#!/usr/bin/env python3
"""Revised-vs-superseded disambiguation — item 3 of almanac-template#11.

Closes SCHEMA-V2.md open item #2 (compute `observed.fingerprint_result`) and
resolves the ambiguity flagged in open item #5: when a redirect *and* content
drift are both observed, is the resource `moved` (same thing, relocated) or
`superseded` (a different thing now sits at that URL)? The status table in
SCHEMA-V2.md already answers `revised` unambiguously (same URL + drift, full
stop) — the genuine ambiguity is only on redirect.

Disambiguation, cheapest signal first:
  1. Full-artifact hash still matches the baseline even after redirect ->
     strongest possible evidence -> `moved`.
  2. Full hash drifted, but the LEAD signature (title + first ~500 chars of
     extracted text) still matches `fingerprint.lead_hash` -> the core claim
     is unchanged even though the page churned elsewhere (nav/ads/footer) ->
     `moved`.
  3. Lead signature also drifted -> a different resource -> `superseded`.
  4. No `lead_hash` baseline exists to check -> honest default -> `redirected`
     (per SCHEMA-V2.md: "can't verify equivalence").

`lead_hash` is a second, narrower fingerprint, not a content store — it never
holds page text, only a hash of a normalized excerpt (SCHEMA-V2.md rule:
"catalog, don't host").

Per open item #5's leaning: this PROPOSES a reclassification via issue, it
never writes `status`/`status_since`/`status_source` to the YAML. Read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_links import BLOCK_CODES, UA, DEFAULT_TIMEOUT  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
MAX_BODY_BYTES = 2_000_000
LEAD_CHARS = 500
_PROBE_MARKER = b"\n___ALMANAC_REVISION_PROBE_EOM___"
_TAG_RE = re.compile(rb"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_ANY_TAG_RE = re.compile(rb"<[^>]+>")
_TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_WS_RE = re.compile(r"\s+")


def _fetch(url: str, timeout: float) -> tuple[int, str, bytes] | None:
    """One request: final HTTP status, final URL (post-redirect), and body.

    Returns None on a hard failure (timeout, connection error, curl missing).
    """
    cmd = ["curl", "-sS", "-L", "--max-time", str(int(timeout)), "-A", UA,
           "-w", _PROBE_MARKER.decode() + "%{http_code}|%{url_effective}", url]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout + 5, check=False)
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return None
    idx = proc.stdout.rfind(_PROBE_MARKER)
    if idx == -1:
        return None
    body, meta = proc.stdout[:idx], proc.stdout[idx + len(_PROBE_MARKER):].decode(errors="ignore")
    try:
        code_s, final_url = meta.split("|", 1)
        return int(code_s), final_url, body[:MAX_BODY_BYTES]
    except ValueError:
        return None


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lead_signature(body: bytes) -> str:
    """Normalize title + a short lead excerpt — a signature, never stored content."""
    title_match = _TITLE_RE.search(body)
    title = title_match.group(1) if title_match else b""
    stripped = _ANY_TAG_RE.sub(b" ", _TAG_RE.sub(b" ", body))
    text = (title + b" " + stripped).decode("utf-8", errors="ignore")
    return _WS_RE.sub(" ", text).strip().lower()[:LEAD_CHARS]


def lead_hash(body: bytes) -> str:
    return sha256_hex(lead_signature(body).encode())


def classify(same_url: bool, fingerprint_result: str, lead_result: str) -> str | None:
    """Return the proposed status, or None if no reclassification is warranted."""
    if fingerprint_result == "match":
        return None if same_url else "moved"
    if fingerprint_result != "drift":
        return None
    if same_url:
        return "revised"
    if lead_result == "same":
        return "moved"
    if lead_result == "different":
        return "superseded"
    return "redirected"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, metavar="SEC")
    args = ap.parse_args()

    report = []
    proposals = 0
    for path in sorted(CATALOG.glob("*.yaml")):
        entry = yaml.safe_load(path.read_text())
        fp = entry.get("fingerprint") or {}
        baseline_sha = fp.get("sha256")
        if not baseline_sha:
            continue  # no baseline captured while live -- nothing to diff against

        entry_id = entry.get("id")
        canonical_url = (entry.get("source") or {}).get("canonical_url")
        declared_status = entry.get("status")
        fetched = _fetch(canonical_url, args.timeout)
        if fetched is None:
            report.append({"id": entry_id, "url": canonical_url, "fingerprint_result": "unreachable",
                           "declared_status": declared_status, "proposed_status": None})
            continue

        code, final_url, body = fetched
        if code in BLOCK_CODES:
            report.append({"id": entry_id, "url": canonical_url, "fingerprint_result": "blocked",
                           "declared_status": declared_status, "proposed_status": None,
                           "note": f"bot-defense block ({code}) -- cannot auto-verify content"})
            continue

        cur_sha = sha256_hex(body)
        fingerprint_result = "match" if cur_sha == baseline_sha else "drift"
        same_url = (final_url.rstrip("/") == (canonical_url or "").rstrip("/"))

        baseline_lead = fp.get("lead_hash")
        cur_lead = lead_hash(body)
        if fingerprint_result == "drift" and not same_url:
            lead_result = "unverifiable" if not baseline_lead else (
                "same" if cur_lead == baseline_lead else "different")
        else:
            lead_result = "unverifiable"

        proposed = classify(same_url, fingerprint_result, lead_result)
        flagged = bool(proposed) and proposed != declared_status
        if flagged:
            proposals += 1

        report.append({
            "id": entry_id, "url": canonical_url, "final_url": final_url,
            "declared_status": declared_status, "fingerprint_result": fingerprint_result,
            "lead_result": lead_result, "proposed_status": proposed if flagged else None,
            "flagged": flagged,
        })

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for r in report:
            mark = "PROPOSE" if r.get("flagged") else "ok     "
            print(f"[{mark}] {r['id']:34} fp={r.get('fingerprint_result','?'):11} "
                  f"declared={r.get('declared_status','?'):10} proposed={r.get('proposed_status') or '-'}")
        print(f"\n{proposals}/{len(report)} baselined entries warrant a proposed reclassification")
    return 1 if proposals else 0


if __name__ == "__main__":
    raise SystemExit(main())
