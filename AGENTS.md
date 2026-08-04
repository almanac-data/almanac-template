# Agent guide — Almanac vertical

Instructions for any AI coding agent (Claude Code, Codex, Cursor, compatible CLIs)
working in an Almanac catalog repository. Read this before making changes.

## What this project is

An Almanac is an **open, versioned index of public data** — a catalog, not a data warehouse.
Each entry in `catalog/` is a human-reviewed, machine-validated record pointing to an
authoritative dataset (canonical source, how to access it, where it's archived, and whether
it's still reachable). It exists to be the curation-and-reachability layer that scattered
public data lacks.

This repository was built from `almanac-template`. The vertical's identity (name, domain,
homepage) lives in `almanac.config.yml`; the schema, scripts, and CI are domain-agnostic and
read from it. **Do not hardcode domain-specific names into the engine** — put them in config.

## The one rule that defines the project

**Catalog, don't host.** This repo maps data; it does not store data bytes. Do not add datasets,
CSVs, NetCDF, GeoTIFFs, or any data payload to the repo. The *only* exception is a deliberate,
small, at-risk artifact recorded as a `recovery[]` candidate — and only after it's been discussed
in an issue. If a task tempts you to commit data, stop: the answer is almost always a catalog
entry pointing to where the data lives.

## Repository map

```
almanac.config.yml                 this vertical's identity (name/slug/description/homepage/domain)
schema/catalog-entry.schema.json   the contract every entry must satisfy (JSON Schema 2020-12)
catalog/<id>.yaml                  one curated dataset per file (source of truth)
catalog.json                       GENERATED build artifact — do not hand-edit
scripts/validate.py                schema + filename==id + uniqueness checks (CI gate)
scripts/build_index.py             catalog/*.yaml -> catalog.json
scripts/check_links.py             reachability checker (reports; writes `observed` only with --write-observed)
scripts/alert_on_dead_links.py     turns a reachability report into GitHub issues (idempotent)
.github/workflows/ci.yml           runs validate + a stale-index guard on every PR
.github/workflows/link-check.yml   daily reachability sweep + dead-link alerting; opens an
                                   `observed`-refresh PR when the probe sees something new
```

This file is propagated verbatim to every vertical, so it describes **only what every
vertical has**. Tooling that lives in `almanac-template` alone — the recovery bot and the
rot/drift checkers — is documented in [`docs/ENGINE-TOOLING.md`](docs/ENGINE-TOOLING.md),
which does not propagate. Adding a template-only path to the map above would hand eleven
verticals a guide pointing at files they do not have.

## Working rules / invariants

1. **The schema is the contract.** Every `catalog/*.yaml` must validate against
   `schema/catalog-entry.schema.json`. Run `python scripts/validate.py` before committing.
2. **Filename equals id.** `catalog/foo-bar.yaml` must contain `id: foo-bar` (kebab-case).
3. **Rebuild the index after touching entries.** Run `python scripts/build_index.py` and
   commit the updated `catalog.json` in the same change. CI fails if it's stale.
4. **Never hand-edit `catalog.json`.** It is generated. Edit the YAML, regenerate.
5. **Verify before you assert.** Do not invent `observed.checked` dates or URL reachability.
   If you can reach the network, confirm `source.canonical_url` and set `observed.checked` to
   today (`YYYY-MM-DD`). If you cannot verify, say so in the PR — do not fabricate.
   **`observed` is machine-written.** Set `checked` and leave `reachable`, `http_status`, and
   `final_url` null — only `scripts/check_links.py --write-observed` fills those, from a real
   probe. Recording your own `curl` output there disguises a human check as a machine one.
   Report what you observed in the PR body; `status` + `status_source: curator` is where a
   human call belongs.
6. **Set `status` honestly:** `live`, `revised`, `moved`, `redirected`, `superseded`, `dark`,
   `frozen` — see `CONTRIBUTING.md` for the full table. If you mark something `dark`/
   `superseded`, add a `notes` line and, if you have one, a `recovery[]` candidate.
7. **Authoritative sources only.** Point to the publisher's canonical home, not a reposting.
8. **One dataset = one file = one PR.** Keep changes small and reviewable.

## Common tasks

```bash
pip install -r requirements.txt
python scripts/validate.py       # before any commit that touches catalog/
python scripts/build_index.py    # regenerate catalog.json after entry changes
python scripts/check_links.py    # verify which sources are still reachable (requires curl)
```

**Recording what the probe saw.** `check_links.py` reports and exits; it changes nothing
unless asked. `--write-observed` writes each probe's facts — `checked`, `reachable`,
`http_status`, `final_url`, `redirect_chain`, and `fingerprint_result` where a baseline
exists — into the matching entry's `observed` block, and nothing else. `status` is never
touched: the machine records what it saw, a curator decides what it means.

```bash
python scripts/check_links.py --write-observed && python scripts/build_index.py
```

Rebuild the index in the same change, since `observed` is carried into `catalog.json`.

**CDN-bot-protected sources.** Some federal hosts (BLS, Census, Congress.gov, SEC, GAO)
sit behind bot protection that curl can't pass, so they show as `blocked / unverifiable`
rather than `ok`. To verify them, set `reachability.headless: true` in `almanac.config.yml`
and install the optional headless dependency, then run with `--headless` (CI does this
automatically when the config flag is on):

```bash
pip install -r requirements-headless.txt && playwright install --with-deps chromium
python scripts/check_links.py --headless
```

The headless rung only ever *upgrades* a blocked source to `ok`; it never flags one as dead.

To add a dataset: copy `catalog/example-dataset.yaml`, fill every required field, validate,
rebuild the index, open a PR. See `CONTRIBUTING.md` for the full checklist.

## Licensing

Catalog data (`catalog/`, `catalog.json`) is **CC0**; tooling (`scripts/`, schema, CI) is
**MIT**. Keep new tooling MIT-compatible and keep entries attribution-accurate — every entry
must credit its publisher in the `attribution` field, even though the index itself is CC0.

## Tone

This is public-interest infrastructure. Accuracy beats coverage: a small, correct, current
catalog is worth more than a large stale one. When unsure whether something is verifiable,
under-claim rather than over-claim.
