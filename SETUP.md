# Setting up your almanac

You've created a new repository from `almanac-template`. Here's how to turn it into a live,
self-monitoring catalog. The whole thing is designed so you never touch the engine — you edit
config and add data.

## 1. Configure your vertical

Edit **`almanac.config.yml`**:

```yaml
name: "Health Almanac"
slug: "health-almanac"
description: "An open, versioned index of public health data."
homepage: "https://github.com/almanac-data/health-almanac"
domain: "health"
```

- `name` / `description` appear in the generated `catalog.json`.
- `slug` + `homepage` form the link-checker's User-Agent, so agencies you probe can see who's checking.

## 2. Replace the README

The repo's `README.md` is the *template's* README (it pitches the template itself). Replace it
with your vertical's README — a starter is provided at **`docs/README.vertical.md`**:

```bash
cp docs/README.vertical.md README.md   # then fill in {Your Almanac Name} and {domain}
```

## 3. Point the issue forms at your repo

In **`.github/ISSUE_TEMPLATE/config.yml`**, replace `YOUR-ALMANAC` with your repo name in both
`contact_links` URLs so the "Contribution guide" and "Agent guide" links resolve.

## 4. Add your first dataset

1. Copy `catalog/example-dataset.yaml` to `catalog/<your-id>.yaml`.
2. Fill in every required field (the filename minus `.yaml` must equal the `id`).
3. Verify the canonical URL yourself; set `last_checked` to today (`YYYY-MM-DD`).
4. Delete `catalog/example-dataset.yaml`.
5. Regenerate and validate:
   ```bash
   pip install -r requirements.txt
   python scripts/validate.py
   python scripts/build_index.py
   ```
6. Commit `catalog/<your-id>.yaml` **and** the updated `catalog.json`. Open a PR; CI gates it.

## 5. Turn on the monitor

The daily reachability sweep (`.github/workflows/link-check.yml`) runs on a 12:00 UTC cron and
opens a GitHub issue when a `live`/`frozen` source goes unreachable. It needs no setup beyond
the default `GITHUB_TOKEN` — but confirm **Settings → Actions → General → Workflow permissions**
is set to *Read and write* so the alert step can open issues. Run it once via
**Actions → link-check → Run workflow** to confirm it's green.

## 6. Recruit curators

Add a `CODEOWNERS` file naming the maintainer(s) for this vertical so PRs route to whoever
stewards it. The Almanac model is one steward per vertical — the org owns the engine, you own
the contents.

That's it. You now have a self-validating, self-monitoring public catalog.
