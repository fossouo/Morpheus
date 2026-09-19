#!/usr/bin/env python3
"""Replay EXP-049 with only the repository import bootstrap corrected."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import evaluate_deepcopy_window_mutation as prior  # noqa: E402


DEFAULT_FIXTURE = prior.DEFAULT_FIXTURE
PRIOR_EXPERIMENT = ROOT / "experiments" / "EXP-049-deepcopy-window-mutation.md"
PRIOR_EXPERIMENT_SHA256 = (
    "a8a9297c255b1d59ba0a86fad8c18ee90ddf9b67d58694702a6de366bf46592d"
)


def load_replay_fixture(path: Path) -> tuple[dict[str, object], int]:
    prior_bytes = PRIOR_EXPERIMENT.read_bytes()
    if hashlib.sha256(prior_bytes).hexdigest() != PRIOR_EXPERIMENT_SHA256:
        raise ValueError("prior-experiment-hash-mismatch")
    fixture, fixture_bytes = prior.load_fixture(path)
    if (
        fixture["expected_baseline_correct"] != 1
        or fixture["expected_candidate_correct"] != 2
        or fixture["expected_baseline_silent_drifts"] != 1
        or fixture["expected_candidate_detected_mutations"] != 1
        or fixture["expected_candidate_error"]
        != "source-changed-during-copy-window"
    ):
        raise ValueError("EXP-049 thresholds changed")
    return fixture, fixture_bytes + len(prior_bytes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    started = perf_counter()
    fixture, fixture_bytes = load_replay_fixture(args.fixture)
    first = prior.run_trial(fixture)
    second = prior.run_trial(fixture)
    summary = dict(first)
    summary.update(
        {
            "replay_of": "EXP-049",
            "repeatable": first == second,
            "fixture_bytes": fixture_bytes,
            "evaluation_seconds": perf_counter() - started,
            "external_calls": 0,
        }
    )
    summary["accepted"] = prior.accepted(summary, fixture)
    summary["evaluation_seconds"] = round(summary["evaluation_seconds"], 6)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
