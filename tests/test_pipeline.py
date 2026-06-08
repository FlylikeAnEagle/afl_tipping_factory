"""Tests for the full pipeline."""

import os
from src.pipeline import run_pre_round, run_post_round


BASE = os.path.join(os.path.dirname(__file__), "..")
FIXTURE_CSV = os.path.join(BASE, "data", "fixtures", "sample_round12_2025.csv")
ODDS_CSV = os.path.join(BASE, "data", "odds", "sample_round12_2025.csv")
RESULTS_CSV = os.path.join(BASE, "data", "results", "sample_round12_2025.csv")


class TestPipeline:
    def test_pre_round_pipeline(self, db_path):
        teams = [
            "Adelaide", "Brisbane", "Carlton", "Collingwood", "Essendon",
            "Fremantle", "Geelong", "Gold Coast", "GWS", "Hawthorn",
            "Melbourne", "North Melbourne", "Port Adelaide", "Richmond",
            "St Kilda", "Sydney", "West Coast", "Western Bulldogs",
        ]
        run_pre_round(FIXTURE_CSV, ODDS_CSV, 2025, 12, teams=teams, db_path=db_path)

    def test_post_round_pipeline(self, db_path):
        teams = [
            "Adelaide", "Brisbane", "Carlton", "Collingwood", "Essendon",
            "Fremantle", "Geelong", "Gold Coast", "GWS", "Hawthorn",
            "Melbourne", "North Melbourne", "Port Adelaide", "Richmond",
            "St Kilda", "Sydney", "West Coast", "Western Bulldogs",
        ]
        run_pre_round(FIXTURE_CSV, ODDS_CSV, 2025, 12, teams=teams, db_path=db_path)
        summary = run_post_round(RESULTS_CSV, 2025, 12, db_path=db_path)

        assert "elo_baseline" in summary
        assert "bookie_favourite" in summary
        assert summary["elo_baseline"]["total"] == 9
        assert summary["bookie_favourite"]["total"] == 9
