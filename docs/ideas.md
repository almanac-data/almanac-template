# almanac-template — idea pile

The hub's open items, in the shape [willow-reconciler](https://pypi.org/project/willow-reconciler/)
reads: top-level `N. ` items, optional legend tags, stable numbers. This file is read by

```sh
reconciler run --repo ./ --doc docs/ideas.md --validate
```

(`./`, not `.`: reconciler 0.6.0 treats a bare `.` as a repo *name* to look up beside the
checkout, and only a string carrying a `/` as a path.)

This file is **template-only**: `docs/` is not in the propagation allowlist in
`.github/workflows/propagate-engine.yml`, so it never reaches a vertical. The eleven verticals
carry no idea pile; see `docs/ENGINE-TOOLING.md`.

Legend: ✅ shipped · 🟡 partial · (untagged) proposed

**Numbers are permanent join keys.** `reconciler/ids.py` derives `<corpus>-ideas-<num>` from the
number written on the line, so a number is an identity, not an ordinal. Never renumber; never
write a markdown-auto-numbered list — retire a number instead and leave the gap. (In
willow-reconciler 0.6.0 the corpus is fixed at `willow`, so ids here read `willow-ideas-NNN`.)

A tag is only ever written where git history shows the landing, and it leads the item text.
Every item below names where it was carried from; nothing here was invented for this file.

---

## A. Schema v2 — the open items carried from `SCHEMA-V2.md`

`SCHEMA-V2.md`'s "Open items before code" list, with its own 2026-08-04 post-mortem: item 2 was
marked done on 2026-07-22 (`bd5cf53`) and was not, and the overstatement was recorded rather
than overwritten "because a status line claiming more than shipped is exactly how the gap
survived unnoticed". Item 3 below is the same shape, found the same way.

1. ✅ **shipped**: generate `schema/catalog-entry.schema.json` v2 from the rationale. Landed as `68837d7` (v2 JSON Schema, 2026-06-30) and `2c58765` (cutover to canonical, 2026-07-01).
2. ✅ **shipped**: update `scripts/check_links.py` to populate `observed` (capture `final_url`, redirect chain) and compute `fingerprint_result` against any baseline. Landed as `e8e4119` (2026-08-04) via `--write-observed`, opt-in so the default stays read-only; `fingerprint_result` is computed only where a `fingerprint.sha256` baseline exists, and a partial read never manufactures a `drift`.
3. Teach `scripts/validate.py` the type-conditional soft-warn for `coverage` vs `bibliographic`. `SCHEMA-V2.md` has marked this done since `bd5cf53`, but `scripts/validate.py` has exactly one commit in its history (`da4674e`, the initial import) and neither word appears in it; only the schema knows `bibliographic`. Not tagged here because the history does not show it.
4. ✅ **shipped**: write `scripts/migrate_v1_v2.py`. Landed as `294ad6f` (#16, 2026-07-01); the mechanical mappings are automated, `type`, fingerprint baselines and `recovery.authenticity` tiers are flagged for human review.
5. 🟡 **partial**: decide whether the daily job auto-promotes `live` → `revised`/`superseded`/`dark`, or only *proposes* a status change via issue for curator confirmation (leaning: propose, never auto-write a lifecycle label). Half settled by construction in `b6dbbe5`: the daily job writes `observed` and opens a `monitor/observed-refresh` PR, and no automation writes `status`, `status_source` or `status_since`. Still open: whether a machine may ever *propose* a status change on its own (an issue, a PR body, a label), and on what evidence; `final_url` differing from `source.canonical_url` is the obvious first candidate.
6. A full `status_history[]` — the maximal version of the bitemporal boundary, deferred in `SCHEMA-V2.md` because `status` + `status_since` is the 80/20.

## B. The Jeles-backed bot — the scope list from issue #11

Six items in rough priority order, under the non-negotiable constraint that the bot proposes via
PR or issue and never auto-merges a lifecycle or authenticity change. Items 7–9 landed
template-only (see `docs/ENGINE-TOOLING.md`); the open design question in #11 — a remote-callable
Jeles endpoint versus a self-hosted runner with fleet access — resolved toward `jeles-remote`.

7. ✅ **shipped**: recovery-candidate discovery — when an entry flips to `dark`/`superseded`, search trusted institutional sources and web archives for replacement candidates and open a PR proposing `recovery[]` additions with a suggested `authenticity` tier. Landed as `9f9ac8c` (`scripts/recovery_bot.py`, `.github/workflows/recovery-bot.yml`, weekly, needs `JELES_REMOTE_SECRET`).
8. ✅ **shipped**: archive-rot recheck — periodically re-probe existing `recovery[].url` values, because Wayback links die too and monitoring the monitor is the whole thesis of this catalog. Landed as `dfaf48f` (`scripts/check_recovery_rot.py`); inert until a vertical populates `recovery[]`.
9. ✅ **shipped**: `revised` vs `superseded` disambiguation — diff the *claims* a page makes before and after a fingerprint drift, not just the hash. Landed as `deada12` (`scripts/check_revision_drift.py`, lead-signature fingerprint); proposes a reclassification only, never assigns `status`.
10. `collection` computation — surface groups of entries that share a verifiable trait (domain, dark-date) as a suggested `collection` id, computed not asserted.
11. `bibliographic` auto-fill — for `type: paper/textbook`, resolve DOI/arXiv/PMID metadata from Crossref, arXiv and PubMed.
12. Entry discovery — sweep topics across institutional sources for newly published resources not yet catalogued; coverage expansion, separate from recovery.

## C. Propagation and the engine boundary

What the hub pushes into eleven verticals, and what it deliberately does not. Sources: issue #29,
the promotion checklist in `docs/ENGINE-TOOLING.md`, the two-lists comment in
`.github/workflows/propagate-engine.yml`, and the fleet's Wave 4/5 plan.

13. Decide whether `.gitignore` joins the propagation allowlist (#29). The anchored ignore rule from #28 protects the template only; the options on the table are leave it, add `.gitignore` to the allowlist (a vertical loses local ignore autonomy), or propagate a `.gitignore.engine` fragment each vertical includes.
14. Harden the `git add -A` in `propagate-engine.yml`'s vertical checkout (#29) — the same command that captured the sibling symlinks originally; safe today only because the copy step is allowlisted, and one allowlist edit away from shipping something unintended.
15. Promote the recovery bot to an engine path only as a deliberate per-vertical act: `recovery-bot.yml` will not run without `JELES_REMOTE_SECRET`, so propagating it installs a workflow that fails on schedule in eleven repositories until eleven secrets exist (`docs/ENGINE-TOOLING.md`).
16. Promote the rot and drift checkers once a vertical carries `recovery[]` candidates or `fingerprint.lead_hash` baselines, with their tests in the same change and their rows moved from `docs/ENGINE-TOOLING.md` into `AGENTS.md`'s map — the step that gets forgotten (`docs/ENGINE-TOOLING.md`).
17. One path list shared by `propagate-engine.yml` and `propagate-engine.sh`; `SETUP.md` added to it; climate's overrides honoured by name; `status-all.sh` covers all eleven; stray `catalog-entry.v2.schema.json` removed by propagation; CODEOWNERS placeholder substituted at propagation time (Wave 5, A5-paths-align).
18. `engine_version` in `almanac.config.yml` written by propagation; `pyproject.toml` leaves the propagated set; a propagated `tests/test_engine_version.py` fails when a vertical's declared version trails the template's (Wave 5, A5-engine-version).
19. 🟡 **partial**: the fleet Dependabot pack applied to the hub and propagated (Wave 4, C4-almanac-dependabot). The pack and its allowlist entry landed in the hub; the eleven propagation PRs open on merge and the operator merges them. `propagate-engine.sh`'s list in the org meta-repo still needs the same one-line addition.

## D. Conventions, governance and docs

The fleet convention this file exists for, and the hub's open issues that are documentation or
governance rather than engine.

20. Adopt `Idea-Id` commit trailers (fleet CONVENTION, decision-2026-09-11).
21. ci: lint Markdown so a doc PR cannot break the README with an unbalanced code fence (#7).
22. governance: a `CODEOWNERS.example` plus a steward rollout checklist (#5); today `docs/STEWARDING.md` carries the onboarding steps in prose and `.github/CODEOWNERS` ships the catch-all.
23. docs: a dead-link triage playbook for stewards (#4).
24. docs: `WHY_ALMANAC` — differentiation versus data.gov and other registries (#3).
25. The headless rung does not beat BLS/SEC bot protection; add a stealth or headed-browser fallback (#2). The rung only ever upgrades `blocked` to `ok`, so the gap is coverage, not a false dead flag.
