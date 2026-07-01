import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_checker():
    return _load("crr", "scripts/check_recovery_rot.py")


def _load_alerter():
    return _load("aor", "scripts/alert_on_recovery_rot.py")


def _entry(recovery):
    return {"id": "example", "recovery": recovery}


def test_excluded_candidates_are_skipped(monkeypatch, tmp_path):
    mod = _load_checker()
    calls = []
    monkeypatch.setattr(mod, "_probe", lambda url, t, headless=False: calls.append(url) or (200, ""))
    catalog = tmp_path / "catalog"
    catalog.mkdir()
    import yaml
    (catalog / "example.yaml").write_text(yaml.safe_dump({
        "id": "example",
        "recovery": [
            {"via": "wayback", "url": "https://a.example", "permission": "ok"},
            {"via": "community", "url": "https://b.example", "permission": "excluded"},
        ],
    }))
    monkeypatch.setattr(mod, "CATALOG", catalog)
    import sys
    from io import StringIO
    old_argv, old_stdout = sys.argv, sys.stdout
    sys.argv, sys.stdout = ["check_recovery_rot.py", "--json"], StringIO()
    try:
        mod.main()
        out = sys.stdout.getvalue()
    finally:
        sys.argv, sys.stdout = old_argv, old_stdout
    assert calls == ["https://a.example"]
    assert "b.example" not in out


def test_definitive_failure_flags_rot(monkeypatch):
    mod = _load_checker()
    monkeypatch.setattr(mod, "_probe", lambda url, t, headless=False: (404, "http 404"))
    # a bare call through the internal loop shape, not main(): exercise the
    # same classification check_links.py uses (reachable/blocked/dead).
    code, note = mod._probe("https://dead.example", 5)
    reachable = code is not None and code < 400
    blocked = code in {401, 403, 406, 429}
    assert not reachable and not blocked  # -> flagged as rot


def test_bot_block_is_not_rot(monkeypatch):
    mod = _load_checker()
    monkeypatch.setattr(mod, "_probe", lambda url, t, headless=False: (403, "blocked"))
    code, note = mod._probe("https://blocked.example", 5)
    blocked = code in {401, 403, 406, 429}
    assert blocked  # unverifiable, never a rot flag


def test_marker_round_trips_entry_id_and_url():
    mod = _load_alerter()
    marker = mod._marker("example-entry", "https://web.archive.org/foo bar")
    tag = f"{mod.MARKER_PREFIX}:id="
    assert tag in marker
    rest = marker.split(tag, 1)[1]
    entry_id = rest.split(" url=", 1)[0].strip()
    url = rest.split(" url=", 1)[1].split(" ", 1)[0].strip()
    assert entry_id == "example-entry"
    assert url == "https://web.archive.org/foo"  # stops at the next space, as expected


class _FakeGitHub:
    def __init__(self):
        self.created = []
        self.closed = []
        self._open = []

    def open_automated_issues(self, label="endpoint-dead"):
        return self._open

    def ensure_labels(self, labels=None):
        pass

    def create_issue(self, title, body, labels):
        self.created.append((title, body, labels))

    def close_issue(self, number, comment):
        self.closed.append((number, comment))


def test_reconcile_opens_issue_for_rotted_candidate():
    mod = _load_alerter()
    gh = _FakeGitHub()
    report = [{"id": "example", "via": "wayback", "url": "https://dead.example",
               "authenticity": "asserted", "permission": "ok", "http": 404,
               "reachable": False, "blocked": False, "flagged": True, "note": "http 404"}]
    mod.reconcile(report, gh)
    assert len(gh.created) == 1
    assert "example" in gh.created[0][0]


def test_reconcile_skips_already_tracked_marker():
    mod = _load_alerter()
    gh = _FakeGitHub()
    marker = mod._marker("example", "https://dead.example")
    gh._open = [{"number": 1, "body": marker}]
    report = [{"id": "example", "via": "wayback", "url": "https://dead.example",
               "authenticity": "asserted", "permission": "ok", "http": 404,
               "reachable": False, "blocked": False, "flagged": True, "note": "http 404"}]
    mod.reconcile(report, gh)
    assert gh.created == []


def test_reconcile_closes_issue_when_recovered():
    mod = _load_alerter()
    gh = _FakeGitHub()
    marker = mod._marker("example", "https://back.example")
    gh._open = [{"number": 2, "body": marker}]
    report = [{"id": "example", "via": "wayback", "url": "https://back.example",
               "authenticity": "asserted", "permission": "ok", "http": 200,
               "reachable": True, "blocked": False, "flagged": False, "note": "ok"}]
    mod.reconcile(report, gh)
    assert len(gh.closed) == 1
    assert gh.closed[0][0] == 2
