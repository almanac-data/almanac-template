# Almanac Template

**A template for building an open, versioned catalog of public data — one that monitors itself for link rot.**

This is the reusable engine behind [The Almanac](https://github.com/almanac-data): a way to
build a **catalog, not a data warehouse**. Each entry is a small, human-reviewed,
machine-validated record pointing to an authoritative public dataset — its canonical source,
how to access it, where it's archived, and whether it is still reachable today. A daily job
probes every source and opens a GitHub issue when one goes dark.

Use it to stand up a new vertical — `health-almanac`, `civic-almanac`, anything where valuable
public data is scattered across institutional URLs that move, rot, or quietly disappear.

## Start a new almanac (≈10 minutes)

1. Click **Use this template → Create a new repository** under the `almanac-data` org.
2. Edit **`almanac.config.yml`** — name, slug, description, homepage, domain. That's the only
   file you must change; the schema, scripts, and CI all read from it.
3. Work through **[SETUP.md](SETUP.md)** — a short post-instantiation checklist.
4. Replace `catalog/example-dataset.yaml` with your first real entry and open a PR.

## What's in the engine

```
almanac.config.yml                 your vertical's identity — the one file you edit
schema/catalog-entry.schema.json   the contract every entry must satisfy
catalog/*.yaml                     one curated dataset per file (your data)
catalog.json                       generated, machine-readable full index
scripts/validate.py                schema + integrity checks (CI gate)
scripts/build_index.py             catalog/*.yaml -> catalog.json
scripts/check_links.py             reachability checker (read-only)
scripts/alert_on_dead_links.py     turns the reachability report into GitHub issues
.github/workflows/ci.yml           validates entries + stale-index guard on every PR
.github/workflows/link-check.yml   daily reachability sweep + auto dead-link alerts
.github/ISSUE_TEMPLATE/            no-code "suggest a dataset" / "report a dead link" forms
```

## The one rule

**Catalog, don't host.** This repo maps data; it does not store data bytes. See
[AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Using a built catalog

```bash
pip install -r requirements.txt
python scripts/validate.py       # check every entry
python scripts/build_index.py    # regenerate catalog.json
python scripts/check_links.py    # report which sources are still reachable
```

## License

- **Catalog data** (`catalog/`, `catalog.json`) — [CC0 1.0](LICENSE-DATA).
- **Tooling** (`scripts/`, schema, CI) — [MIT](LICENSE-CODE).

---

Part of [The Almanac](https://github.com/almanac-data) — a community-maintained commons for
public data that's worth keeping findable.
