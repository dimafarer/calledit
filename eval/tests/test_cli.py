"""Tests for CLI argument parsing and tier composition."""

import sys
import os
import warnings

import pytest

# Suppress requests dependency warning from urllib3/chardet version mismatch
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*urllib3.*")
warnings.filterwarnings("ignore", message=".*chardet.*")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from eval.run_eval import parse_args, build_evaluators


class TestBuildEvaluators:
    """Verify evaluator sets for each tier."""

    def test_smoke_tier_count(self):
        """Smoke tier: 6 creation + 5 verification + 3 mode-specific = 14."""
        evaluators = build_evaluators("smoke")
        assert len(evaluators) == 14

    def test_smoke_judges_tier_count(self):
        """Smoke+judges: 14 smoke + 3 LLM judges + 1 verdict accuracy = 18."""
        evaluators = build_evaluators("smoke+judges")
        assert len(evaluators) == 18

    def test_full_tier_count(self):
        """Full: same as smoke+judges (calibration is post-experiment)."""
        evaluators = build_evaluators("full")
        assert len(evaluators) == 18

    def test_smoke_has_no_llm_judges(self):
        """Smoke tier should not include OutputEvaluator instances."""
        from strands_evals.evaluators import OutputEvaluator
        evaluators = build_evaluators("smoke")
        for e in evaluators:
            assert not isinstance(e, OutputEvaluator), (
                f"Smoke tier should not include LLM judges, found {type(e).__name__}"
            )

    def test_smoke_judges_has_llm_judges(self):
        """Smoke+judges tier should include OutputEvaluator instances."""
        from strands_evals.evaluators import OutputEvaluator
        evaluators = build_evaluators("smoke+judges")
        llm_judges = [e for e in evaluators if isinstance(e, OutputEvaluator)]
        assert len(llm_judges) == 3  # IP, PQ, EQ

    def test_smoke_judges_has_verdict_accuracy(self):
        """Smoke+judges tier should include VerdictAccuracyEvaluator."""
        from eval.evaluators.verification.verdict_accuracy import VerdictAccuracyEvaluator
        evaluators = build_evaluators("smoke+judges")
        va = [e for e in evaluators if isinstance(e, VerdictAccuracyEvaluator)]
        assert len(va) == 1


class TestParseArgs:
    """Verify CLI argument defaults and parsing."""

    def test_defaults(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["run_eval.py"])
        args = parse_args()
        assert args.dataset == "eval/golden_dataset.json"
        assert args.dynamic_dataset is None
        assert args.tier == "smoke"
        assert args.description is None
        assert args.dry_run is False
        assert args.case is None
        assert args.resume is False
        assert args.skip_cleanup is False
        assert args.local_backup is False

    def test_full_tier(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["run_eval.py", "--tier", "full"])
        args = parse_args()
        assert args.tier == "full"

    def test_dry_run(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["run_eval.py", "--dry-run"])
        args = parse_args()
        assert args.dry_run is True

    def test_case_filter(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["run_eval.py", "--case", "base-002"])
        args = parse_args()
        assert args.case == "base-002"

    def test_local_backup(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["run_eval.py", "--local-backup"])
        args = parse_args()
        assert args.local_backup is True

    def test_all_flags(self, monkeypatch):
        monkeypatch.setattr("sys.argv", [
            "run_eval.py",
            "--dataset", "custom.json",
            "--dynamic-dataset", "dynamic.json",
            "--tier", "full",
            "--description", "test run",
            "--case", "base-001",
            "--resume",
            "--skip-cleanup",
            "--local-backup",
        ])
        args = parse_args()
        assert args.dataset == "custom.json"
        assert args.dynamic_dataset == "dynamic.json"
        assert args.tier == "full"
        assert args.description == "test run"
        assert args.case == "base-001"
        assert args.resume is True
        assert args.skip_cleanup is True
        assert args.local_backup is True
