# Development

This repo is tools + data. You only need Python to work on it.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"      # jsonschema, PyYAML, ruff, pytest
python scripts/validate.py
python scripts/build_index.py
ruff check .                 # lint before pushing — config in pyproject.toml
```

## Conventions

- **Worktree + PR for every change.** No direct commits to `main`.
- **Run `ruff check .` before pushing.** Lint CI is enforced.
- **One dataset = one file = one PR.**
- **Rebuild `catalog.json` after touching `catalog/`** and commit it in the same change.

## Optional: agent / fleet overlay

A gitignored `.mcp.json` (and `.willow/`) can wire this folder into an agent fleet for memory +
execution tooling on a maintainer's machine. It references machine-specific absolute paths, is
local-only, and never ships in the public repo (see `.gitignore`). Nothing in the engine depends
on it — anyone can clone and contribute with just Python.
