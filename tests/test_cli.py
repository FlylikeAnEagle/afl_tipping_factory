"""Tests for the CLI entrypoint."""

import subprocess
import sys
import os
import pytest


ROOT = os.path.join(os.path.dirname(__file__), "..")


class TestCLI:
    def test_help_exits(self):
        result = subprocess.run(
            [sys.executable, "-m", "src"],
            capture_output=True, text=True, cwd=ROOT,
        )
        assert result.returncode == 1
        assert "AFL Tipping Factory" in result.stdout

    def test_init_db(self, tmp_path):
        db = str(tmp_path / "cli_test.db")
        result = subprocess.run(
            [sys.executable, "-m", "src", "init-db", "--db", db],
            capture_output=True, text=True, cwd=ROOT,
        )
        assert result.returncode == 0
        assert "initialised" in result.stdout.lower()
        assert os.path.exists(db)

    def test_pre_round_cli(self, tmp_path):
        db = str(tmp_path / "cli_pre.db")
        result = subprocess.run(
            [sys.executable, "-m", "src", "pre-round",
             "--round", "12", "--season", "2025", "--db", db],
            capture_output=True, text=True, cwd=ROOT,
        )
        assert result.returncode == 0
        assert "Loaded 9 fixtures" in result.stdout
        assert "Validation passed" in result.stdout
        assert "elo_baseline_pick" in result.stdout

    def test_post_round_cli(self, tmp_path):
        db = str(tmp_path / "cli_full.db")
        # Pre-round first
        subprocess.run(
            [sys.executable, "-m", "src", "pre-round",
             "--round", "12", "--season", "2025", "--db", db],
            capture_output=True, text=True, cwd=ROOT,
        )
        # Post-round
        result = subprocess.run(
            [sys.executable, "-m", "src", "post-round",
             "--round", "12", "--season", "2025", "--db", db],
            capture_output=True, text=True, cwd=ROOT,
        )
        assert result.returncode == 0
        assert "Loaded 9 results" in result.stdout
        assert "SCORING SUMMARY" in result.stdout
        assert "bookie_favourite" in result.stdout
        assert "elo_baseline" in result.stdout

    def test_post_round_shows_fades(self, tmp_path):
        db = str(tmp_path / "cli_fades.db")
        subprocess.run(
            [sys.executable, "-m", "src", "pre-round",
             "--round", "12", "--season", "2025", "--db", db],
            capture_output=True, text=True, cwd=ROOT,
        )
        result = subprocess.run(
            [sys.executable, "-m", "src", "post-round",
             "--round", "12", "--season", "2025", "--db", db],
            capture_output=True, text=True, cwd=ROOT,
        )
        assert result.returncode == 0
        # Bookie has 0 fades — should show N/A
        assert "N/A" in result.stdout
        # Elo had fades — should show a number
        lines = result.stdout.split("\n")
        elo_line = [l for l in lines if "elo_baseline" in l][0]
        assert "Fades:" in elo_line

    def test_matrix_cli(self, tmp_path):
        db = str(tmp_path / "cli_mat.db")
        subprocess.run(
            [sys.executable, "-m", "src", "pre-round",
             "--round", "12", "--season", "2025", "--db", db],
            capture_output=True, text=True, cwd=ROOT,
        )
        result = subprocess.run(
            [sys.executable, "-m", "src", "matrix",
             "--round", "12", "--season", "2025", "--db", db],
            capture_output=True, text=True, cwd=ROOT,
        )
        assert result.returncode == 0
        assert "TIPPING MATRIX" in result.stdout

    def test_custom_fixture_path(self, tmp_path):
        db = str(tmp_path / "cli_custom.db")
        fixture = os.path.join(ROOT, "data", "fixtures", "sample_round12_2025.csv")
        result = subprocess.run(
            [sys.executable, "-m", "src", "pre-round",
             "--round", "12", "--season", "2025", "--db", db,
             "--fixture", fixture],
            capture_output=True, text=True, cwd=ROOT,
        )
        assert result.returncode == 0
