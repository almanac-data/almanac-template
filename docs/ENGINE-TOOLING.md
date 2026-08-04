# Engine-only tooling

Scripts, workflows, and tests that live in `almanac-template` and **do not propagate** to
verticals. They are absent from `ENGINE_PATHS` in the org meta-repo's
`scripts/propagate-engine.sh`, so a vertical will never receive them.

This file exists so `AGENTS.md` can be propagated verbatim. `AGENTS.md` is copied to all
eleven verticals, so anything it names must exist in all eleven; template-only tooling
documented there would point every vertical at files it does not have. That mismatch is
exactly why `AGENTS.md` sat un-propagated — and stale at v1 everywhere — while the schema
moved on without it.

| Path | What it does |
|------|--------------|
| `scripts/recovery_bot.py` | Proposes `recovery[]` candidates for `dark` / `superseded` entries via jeles-remote. Never auto-writes; opens a PR. |
| `scripts/check_recovery_rot.py` | Re-probes existing `recovery[]` URLs and reports candidates that have themselves gone dark. |
| `scripts/check_revision_drift.py` | Compares `observed.lead_result` against the stored `fingerprint.lead_hash` and proposes a `moved` / `superseded` reclassification. Proposes only — it never assigns `status`. |
| `scripts/alert_on_recovery_rot.py` | Turns a rot report into GitHub issues. |
| `scripts/alert_on_revision_drift.py` | Turns a drift report into GitHub issues. |
| `.github/workflows/recovery-bot.yml` | Weekly recovery-candidate discovery. Requires a `JELES_REMOTE_SECRET` repo secret. |
| `tests/test_recovery_rot.py` | Covers the rot checker. |
| `tests/test_revision_drift.py` | Covers the drift proposer. |

## Why these stay here

Two different reasons, worth keeping straight:

**The recovery bot needs a secret.** `recovery-bot.yml` will not run without
`JELES_REMOTE_SECRET`, so propagating it would install a workflow that fails on schedule in
eleven repositories until someone provisions eleven secrets. Shipping it to a vertical should
be a deliberate per-vertical act, not a side effect of an engine sync.

**The rot and drift checkers are ahead of the catalogs.** They operate on `recovery[]`
candidates and `fingerprint.lead_hash` baselines. No vertical currently has either populated,
so the scripts would be inert — and inert tooling in a repo map is worse than absent tooling,
because it reads as available.

## Promoting one to an engine path

If a vertical should get one of these, the change belongs in the org meta-repo:

1. Add the path to `ENGINE_PATHS` in `scripts/propagate-engine.sh`.
2. Add its tests in the same change — a propagated script with no propagated test is how
   a vertical ends up running code nobody checks.
3. If it needs a secret or config, say so in `AGENTS.md` and confirm every vertical has it
   *before* the first `--apply`.
4. Move its row out of the table above and into `AGENTS.md`'s repository map.

Step 4 is the one that gets forgotten. This file and `AGENTS.md` describe one repository
between them; a path listed in both, or in neither, is a bug.
