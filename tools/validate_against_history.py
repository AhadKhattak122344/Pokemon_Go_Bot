#!/usr/bin/env python3
"""Reject suggestions that match non-retryable experiment history."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / "codex_memory" / "attempted_approaches.json"


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9.+]+", " ", text.casefold()).strip()


def term_matches(term: str, suggestion: str) -> bool:
    term = normalize(term)
    suggestion = normalize(suggestion)
    if not term:
        return False
    return term in suggestion


def load_history(path: Path = MEMORY) -> dict:
    if not path.exists():
        return {"experiments": []}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def check_suggestion(suggestion: str, history: dict | None = None) -> dict:
    history = history or load_history()
    matches = []
    for experiment in history.get("experiments", []):
        retry_allowed = experiment.get("retry_allowed", True)
        if retry_allowed:
            continue
        terms = list(experiment.get("match_terms") or experiment.get("tags", []))
        matched_terms = [term for term in terms if term_matches(str(term), suggestion)]
        if matched_terms:
            matches.append({
                "id": experiment.get("id"),
                "name": experiment.get("name"),
                "status": experiment.get("status"),
                "matched_terms": sorted(set(matched_terms)),
                "reason": experiment.get("failure_reason", "No reason recorded"),
                "alternative": experiment.get("alternative", "No alternative recorded"),
                "source": experiment.get("source"),
            })
    return {"valid": not matches, "matches": matches}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suggestion", nargs="+", help="Suggestion text to check")
    parser.add_argument("--json", action="store_true", help="Print machine-readable result")
    args = parser.parse_args(argv)
    result = check_suggestion(" ".join(args.suggestion))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif result["valid"]:
        print("OK: no non-retryable experiment history matched.")
    else:
        print("BLOCKED: suggestion matches non-retryable experiment history.", file=sys.stderr)
        for match in result["matches"]:
            print(f"- {match['id']} {match['name']}: {match['reason']}", file=sys.stderr)
            print(f"  Alternative: {match['alternative']}", file=sys.stderr)
            if match.get("source"):
                print(f"  Source: {match['source']}", file=sys.stderr)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
