import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "validate_against_history.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_against_history", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_blocks_non_retryable_terms():
    validator = load_validator()
    result = validator.check_suggestion("Try API 34 with MagiskHide and Play Integrity Fix")
    assert result["valid"] is False
    names = {match["name"] for match in result["matches"]}
    assert "api34_arm64_translation_sigill" in names
    assert "archived_identity_concealment_stack" in names


def test_allows_unmatched_new_suggestion():
    validator = load_validator()
    result = validator.check_suggestion("capture read-only package state from a certified physical Android")
    assert result == {"valid": True, "matches": []}


def test_explicit_match_terms_do_not_block_unrelated_gpu_checks():
    validator = load_validator()
    history = {"experiments": [{
        "id": "prior-host-test", "retry_allowed": False,
        "tags": ["gpu"], "match_terms": ["api37 host"],
    }]}
    result = validator.check_suggestion("run api37 software gpu boot comparison", history)
    assert result == {"valid": True, "matches": []}


def test_blocks_now_verified_api37_software_display_failure():
    validator = load_validator()
    result = validator.check_suggestion("run api37 software gpu boot comparison")
    assert result["valid"] is False
    assert any(match["id"] == "L23-L24" for match in result["matches"])


def test_blocks_pasted_integrity_bypass_runbook_terms():
    validator = load_validator()
    result = validator.check_suggestion("use LSPosed, YASNAC, Pixel 8 fingerprint and residential proxy")
    assert result["valid"] is False
    names = {match["name"] for match in result["matches"]}
    assert "pasted_play_integrity_bypass_runbook" in names
