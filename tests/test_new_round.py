"""Tests for the new-round CLI command."""

import os
import subprocess
import sys
import pytest


ROOT = os.path.join(os.path.dirname(__file__), "..")


def run_cli(*extra_args):
    return subprocess.run(
        [sys.executable, "-m", "src", "new-round"] + list(extra_args),
        capture_output=True, text=True, cwd=ROOT,
    )


def manual_dir(tmp_path):
    """Point the CLI at a tmp data/manual directory by running in isolation."""
    return tmp_path


class TestNewRound:
    def test_creates_three_files(self, tmp_path):
        result = run_cli("--season", "2026", "--round", "14")
        assert result.returncode == 0

        manual = os.path.join(ROOT, "data", "manual")
        for name in [
            f"fixtures_2026_round14.csv",
            f"odds_2026_round14.csv",
            f"results_2026_round14.csv",
        ]:
            path = os.path.join(manual, name)
            assert os.path.exists(path), f"Expected {path}"
            # Cleanup
            os.remove(path)

    def test_output_shows_created_paths(self):
        result = run_cli("--season", "2026", "--round", "14")
        assert "Created:" in result.stdout
        assert "fixtures_2026_round14.csv" in result.stdout
        assert "odds_2026_round14.csv" in result.stdout
        assert "results_2026_round14.csv" in result.stdout
        # Cleanup
        manual = os.path.join(ROOT, "data", "manual")
        for name in [
            f"fixtures_2026_round14.csv",
            f"odds_2026_round14.csv",
            f"results_2026_round14.csv",
        ]:
            p = os.path.join(manual, name)
            if os.path.exists(p):
                os.remove(p)

    def test_does_not_overwrite_existing(self):
        # Create first
        run_cli("--season", "2027", "--round", "1")
        # Write custom content
        manual = os.path.join(ROOT, "data", "manual")
        fix_path = os.path.join(manual, "fixtures_2027_round1.csv")
        original = open(fix_path).read()
        with open(fix_path, "w") as f:
            f.write("CUSTOM_CONTENT_DO_NOT_OVERWRITE\n")

        # Try again without --force
        result = run_cli("--season", "2027", "--round", "1")
        assert "Skipped" in result.stdout
        with open(fix_path) as f:
            assert "CUSTOM_CONTENT_DO_NOT_OVERWRITE" in f.read()

        # Cleanup
        for name in [
            f"fixtures_2027_round1.csv",
            f"odds_2027_round1.csv",
            f"results_2027_round1.csv",
        ]:
            p = os.path.join(manual, name)
            if os.path.exists(p):
                os.remove(p)

    def test_force_overwrites(self):
        manual = os.path.join(ROOT, "data", "manual")
        fix_path = os.path.join(manual, "fixtures_2028_round5.csv")

        # Create first
        run_cli("--season", "2028", "--round", "5")
        with open(fix_path, "w") as f:
            f.write("CUSTOM_CONTENT\n")

        # Force overwrite
        result = run_cli("--season", "2028", "--round", "5", "--force")
        assert "Created:" in result.stdout
        with open(fix_path) as f:
            content = f.read()
        assert "CUSTOM_CONTENT" not in content
        assert "match_id" in content  # Template content

        # Cleanup
        for name in [
            f"fixtures_2028_round5.csv",
            f"odds_2028_round5.csv",
            f"results_2028_round5.csv",
        ]:
            p = os.path.join(manual, name)
            if os.path.exists(p):
                os.remove(p)

    def test_invalid_season_rejected(self):
        result = run_cli("--season", "1999", "--round", "5")
        assert result.returncode != 0

    def test_invalid_round_rejected(self):
        result = run_cli("--season", "2026", "--round", "0")
        assert result.returncode != 0

    def test_round_27_accepted(self):
        """Max round 27 should be valid."""
        result = run_cli("--season", "2026", "--round", "27")
        assert result.returncode == 0
        manual = os.path.join(ROOT, "data", "manual")
        for name in [
            f"fixtures_2026_round27.csv",
            f"odds_2026_round27.csv",
            f"results_2026_round27.csv",
        ]:
            p = os.path.join(manual, name)
            if os.path.exists(p):
                os.remove(p)
