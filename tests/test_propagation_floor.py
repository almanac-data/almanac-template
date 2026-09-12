"""Structural guards on what the hub pushes into the eleven verticals.

Template-only: this file is not in the propagation allowlist, so it runs
in almanac-template alone (docs/ENGINE-TOOLING.md). It reads the workflow
that IS the allowlist rather than a copy of it, so a path added to one
list and not the other fails here instead of silently on the next merge.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "propagate-engine.yml"
DEPENDABOT = ROOT / ".github" / "dependabot.yml"

# Files that must never propagate: the verticals have no idea pile, so a
# trailer gate there would fail every PR, and this test describes the hub.
TEMPLATE_ONLY = (
    ".github/workflows/trailers.yml",
    "docs/ideas.md",
    "tests/test_propagation_floor.py",
)


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text())


def _trigger_paths(wf) -> list[str]:
    # PyYAML reads a bare `on:` key as the boolean True (YAML 1.1).
    on = wf.get("on", wf.get(True))
    return list(on["push"]["paths"])


def _copied_paths(wf) -> list[str]:
    steps = wf["jobs"]["propagate"]["steps"]
    run = next(s["run"] for s in steps if s.get("id") == "copy")
    m = re.search(r"paths=\(\n(.*?)\n\s*\)", run, re.DOTALL)
    assert m, "could not find the paths=( ... ) array in the copy step"
    return [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]


def test_dependabot_pack_exists_and_names_both_ecosystems():
    cfg = yaml.safe_load(DEPENDABOT.read_text())
    assert cfg["version"] == 2
    by_eco = {u["package-ecosystem"]: u for u in cfg["updates"]}
    assert set(by_eco) == {"github-actions", "pip"}
    for u in by_eco.values():
        assert u["directory"] == "/"
        assert u["schedule"]["interval"] == "weekly"
    groups = by_eco["pip"]["groups"]
    grouped = {t for g in groups.values() for t in g["update-types"]}
    assert grouped == {"minor", "patch"}, "pip minor and patch bumps travel as one PR"


def test_dependabot_pack_is_propagated():
    wf = _workflow()
    assert ".github/dependabot.yml" in _trigger_paths(wf)
    assert ".github/dependabot.yml" in _copied_paths(wf)


def test_trigger_and_copy_lists_agree():
    # The workflow carries the allowlist twice: what wakes it and what it
    # copies. A path in one and not the other either never propagates or
    # propagates only when something else changes.
    wf = _workflow()
    assert sorted(_trigger_paths(wf)) == sorted(_copied_paths(wf))


def test_template_only_files_are_not_propagated():
    wf = _workflow()
    copied = set(_copied_paths(wf)) | set(_trigger_paths(wf))
    for rel in TEMPLATE_ONLY:
        assert rel not in copied, f"{rel} is hub-only and must not reach a vertical"
    # No directory-wide entry could sweep them in either.
    assert not any(p.endswith("/") or "*" in p for p in copied)
