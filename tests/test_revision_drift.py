import hashlib
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_checker():
    return _load("crd", "scripts/check_revision_drift.py")


def _load_alerter():
    return _load("aord", "scripts/alert_on_revision_drift.py")


# ── classify() — the core disambiguation logic ────────────────────────────

def test_same_url_drift_is_revised():
    mod = _load_checker()
    assert mod.classify(same_url=True, fingerprint_result="drift", lead_result="unverifiable") == "revised"


def test_same_url_match_is_no_change():
    mod = _load_checker()
    assert mod.classify(same_url=True, fingerprint_result="match", lead_result="unverifiable") is None


def test_redirect_full_hash_match_is_moved():
    mod = _load_checker()
    assert mod.classify(same_url=False, fingerprint_result="match", lead_result="unverifiable") == "moved"


def test_redirect_drift_lead_same_is_moved():
    mod = _load_checker()
    assert mod.classify(same_url=False, fingerprint_result="drift", lead_result="same") == "moved"


def test_redirect_drift_lead_different_is_superseded():
    mod = _load_checker()
    assert mod.classify(same_url=False, fingerprint_result="drift", lead_result="different") == "superseded"


def test_redirect_drift_no_lead_baseline_is_honest_default():
    mod = _load_checker()
    assert mod.classify(same_url=False, fingerprint_result="drift", lead_result="unverifiable") == "redirected"


def test_no_baseline_result_never_reclassifies():
    mod = _load_checker()
    assert mod.classify(same_url=True, fingerprint_result="no-baseline", lead_result="unverifiable") is None


# ── lead_signature / lead_hash — the "second fingerprint" ──────────────────

def test_lead_signature_strips_tags_and_normalizes_whitespace():
    mod = _load_checker()
    body = b"<html><title>  Climate  Data  </title><body>  Hello   World  </body></html>"
    sig = mod.lead_signature(body)
    assert "<" not in sig and ">" not in sig
    assert "  " not in sig  # collapsed whitespace
    assert sig == sig.lower()


def test_lead_signature_strips_script_and_style_blocks():
    mod = _load_checker()
    body = b"<html><script>evil()</script><style>.x{color:red}</style><title>T</title>real content</html>"
    sig = mod.lead_signature(body)
    assert "evil" not in sig
    assert "color" not in sig
    assert "real content" in sig


def test_lead_hash_is_stable_for_identical_normalized_content():
    mod = _load_checker()
    a = b"<title>Same</title><p>Body text here.</p>"
    b = b"<title>Same</title>\n\n<p>Body   text here.</p>"  # whitespace-only diff
    assert mod.lead_hash(a) == mod.lead_hash(b)


def test_lead_hash_differs_when_title_changes():
    mod = _load_checker()
    a = b"<title>Original Dataset</title><p>Body text.</p>"
    b = b"<title>Totally Different Page</title><p>Body text.</p>"
    assert mod.lead_hash(a) != mod.lead_hash(b)


def test_sha256_hex_matches_stdlib():
    mod = _load_checker()
    data = b"hello world"
    assert mod.sha256_hex(data) == hashlib.sha256(data).hexdigest()


# ── alert_on_revision_drift.py — proposal issue lifecycle ──────────────────

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

    def update_issue_body(self, number, body):
        pass

    def close_issue(self, number, comment):
        self.closed.append((number, comment))


def _report_row(**overrides):
    row = {"id": "example", "url": "https://example.org", "final_url": "https://new.example.org",
           "declared_status": "live", "fingerprint_result": "drift", "lead_result": "different",
           "proposed_status": "superseded", "flagged": True}
    row.update(overrides)
    return row


def test_reconcile_opens_proposal_for_flagged_entry():
    mod = _load_alerter()
    gh = _FakeGitHub()
    mod.reconcile([_report_row()], gh)
    assert len(gh.created) == 1
    assert "superseded" in gh.created[0][0]


def test_reconcile_never_touches_yaml_only_issues():
    # Structural guarantee: reconcile()'s only side effects go through the
    # GitHub client (create/update/close issue) -- no file I/O in this module.
    mod = _load_alerter()
    import inspect
    src = inspect.getsource(mod.reconcile)
    assert "open(" not in src and "yaml" not in src.lower()


def test_reconcile_closes_stale_proposal_when_no_longer_flagged():
    mod = _load_alerter()
    gh = _FakeGitHub()
    marker = mod._marker("example")
    gh._open = [{"number": 3, "body": marker}]
    unflagged_row = _report_row(flagged=False, proposed_status=None)
    mod.reconcile([unflagged_row], gh)
    assert len(gh.closed) == 1
    assert gh.closed[0][0] == 3
