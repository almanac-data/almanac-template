# Contributing

Thank you for helping keep public data findable. Contributions are deliberately small and
reviewable: **one dataset = one file = one pull request.**

## Add a dataset

1. Copy `catalog/example-dataset.yaml` as a starting point.
2. Create `catalog/<your-id>.yaml`. The filename (minus `.yaml`) **must** equal the entry's `id`,
   a kebab-case slug (e.g. `agency-sea-level-rise`).
3. Fill in every required field (see `schema/catalog-entry.schema.json`). Required:
   `id, type, title, description, publisher, topics, source, access, status, observed, license,
   attribution`.
4. Verify the source URL yourself and set `observed.checked` to today's date (`YYYY-MM-DD`).
5. Run the checks locally:
   ```bash
   pip install -r requirements.txt
   python scripts/validate.py
   python scripts/build_index.py
   ```
6. Open a PR. CI runs validation; a green check is required to merge.

No coding? You can also **[suggest a dataset](../../issues/new/choose)** with a short form and a
curator will turn it into an entry.

## Status values

Set `status` honestly based on what `observed` actually shows — never by motive (see
`SCHEMA-V2.md` for the full rationale):

| status       | meaning                                                              |
|--------------|-----------------------------------------------------------------------|
| `live`       | reachable and current                                                |
| `revised`    | reachable, same URL, content has drifted from the baseline           |
| `moved`      | redirected, content verified equivalent to the baseline              |
| `redirected` | redirected, equivalence not verified (the honest default)            |
| `superseded` | reachable but serving materially different content than the original |
| `dark`       | unreachable, or a persistent 4xx/5xx                                 |
| `frozen`     | reachable but publisher-declared static                              |

If you mark something `dark` or `superseded`, add a note in `notes` explaining what you found, and
if possible a `recovery[]` candidate (see below).

## Curation principles

- **Authoritative sources only.** Point to the publisher's canonical home, not a blog reposting it.
- **No data in this repo.** We catalog; we don't host bytes. `recovery[]` *points* to copies
  elsewhere — it never hosts one here.
- **Recovery ranks by authenticity, never authority.** `recovery[]` candidates are ordered by
  verifiable fidelity (`hash-verified` > `cross-archive` > `timestamped` > `asserted`), not by who
  runs the mirror. `permission` is a gate (`ok` / `review` / `excluded`), not a rank.
- **Provenance and attribution are mandatory.** Every entry must credit its publisher.
- **Accuracy over coverage.** A small, correct, current catalog beats a large stale one.

## Reporting a dead link

Open an issue (or a PR flipping the entry's `status`) if you find a source has gone dark or moved.
Reachability reports from `scripts/check_links.py` are welcome.
