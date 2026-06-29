# Stewarding an Almanac vertical

This catalog is a community-maintained index of public datasets in its domain — a map of where
the data lives, not a copy of the data itself. Each entry is one small YAML file pointing to an
authoritative source, with how to access it and whether it's still reachable. A daily job
re-checks every link and flags anything that's gone dark.

As steward, you own the *contents*, not the machinery. The engine — schema, validation, the
reachability monitor — is shared across all of The Almanac's verticals and maintained upstream;
you don't touch it. Your job is curation judgment: approve good entries, keep statuses honest,
and decide what's worth cataloging.

Day to day that means: reviewing the "Suggest a dataset" issues people file (they don't need to
write code — you turn the form into a catalog entry, or merge their PR), confirming a source
actually resolves before you mark it `live`, and triaging the dead-link alerts the monitor opens.
The one rule that defines the project: **catalog, don't host** — never commit data files, only
records pointing to them.

Two principles carry the whole thing: **authoritative sources only** (the publisher's canonical
home, never a reposting) and **accuracy over coverage** (a small, current, correct catalog beats
a big stale one). When unsure something is verifiable, under-claim.

Everything you need is in the repo: `CONTRIBUTING.md` for the entry checklist, `AGENTS.md` for the
schema invariants, and `SETUP.md` for the one-time configuration. Start by reading the entries
already in `catalog/` — they're the template for everything else.
