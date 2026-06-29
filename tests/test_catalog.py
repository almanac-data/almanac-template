import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_validate_passes():
    r = subprocess.run([sys.executable, "scripts/validate.py"], cwd=ROOT)
    assert r.returncode == 0


def test_build_index_sorted_and_unique():
    subprocess.run([sys.executable, "scripts/build_index.py"], cwd=ROOT, check=True)
    data = json.loads((ROOT / "catalog.json").read_text())
    assert data["count"] == len(data["entries"])
    ids = [e["id"] for e in data["entries"]]
    assert ids == sorted(ids), "entries must be sorted by id"
    assert len(ids) == len(set(ids)), "ids must be unique"


def test_schema_is_well_formed():
    from jsonschema import Draft202012Validator
    schema = json.loads((ROOT / "schema" / "catalog-entry.schema.json").read_text())
    Draft202012Validator.check_schema(schema)


def test_checker_classifies_bot_blocks():
    spec = importlib.util.spec_from_file_location("cl", ROOT / "scripts" / "check_links.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Block codes are treated as "unverifiable", never as a dead-link flag.
    assert {401, 403, 406, 429} <= mod.BLOCK_CODES
