"""Tests for CSV loaders."""

import os
import pandas as pd
import pytest
from src.loaders import load_fixtures, load_odds, load_results
from src.db import get_connection


FIXTURE_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "sample_round12_2025.csv")
ODDS_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "odds", "sample_round12_2025.csv")
RESULTS_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "results", "sample_round12_2025.csv")


class TestLoadFixtures:
    def test_load_sample_fixtures(self, initialized_db):
        count = load_fixtures(FIXTURE_CSV, initialized_db)
        assert count == 9

        conn = get_connection(initialized_db)
        rows = conn.execute("SELECT * FROM matches").fetchall()
        conn.close()
        assert len(rows) == 9

    def test_fixture_fields(self, initialized_db):
        load_fixtures(FIXTURE_CSV, initialized_db)
        conn = get_connection(initialized_db)
        row = conn.execute("SELECT * FROM matches WHERE match_id = '2025R12PiesDons'").fetchone()
        conn.close()

        assert row["home_team"] == "Collingwood"
        assert row["away_team"] == "Essendon"
        assert row["venue"] == "MCG"
        assert row["round"] == 12
        assert row["neutral_venue"] == 0

    def test_duplicate_fixtures_ignored(self, initialized_db):
        load_fixtures(FIXTURE_CSV, initialized_db)
        count = load_fixtures(FIXTURE_CSV, initialized_db)  # Second load
        conn = get_connection(initialized_db)
        rows = conn.execute("SELECT * FROM matches").fetchall()
        conn.close()
        assert len(rows) == 9  # No duplicates

    def test_missing_columns_raises(self, initialized_db, tmp_path):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("match_id,home_team\n1,Collingwood\n")
        with pytest.raises(ValueError, match="missing columns"):
            load_fixtures(str(bad_csv), initialized_db)


class TestLoadOdds:
    def test_load_sample_odds(self, initialized_db):
        load_fixtures(FIXTURE_CSV, initialized_db)
        count = load_odds(ODDS_CSV, initialized_db)
        assert count == 9

    def test_odds_preserved_in_matches(self, initialized_db):
        load_fixtures(FIXTURE_CSV, initialized_db)
        load_odds(ODDS_CSV, initialized_db)
        conn = get_connection(initialized_db)
        row = conn.execute("SELECT * FROM matches WHERE match_id = '2025R12PiesDons'").fetchone()
        conn.close()
        assert row["home_odds"] == 1.40
        assert row["away_odds"] == 2.90
        assert row["market_source"] == "manual_sportsbet"

    def test_manual_odds_not_overwritten(self, initialized_db, tmp_path):
        """Non-manual odds must not overwrite manual odds."""
        load_fixtures(FIXTURE_CSV, initialized_db)
        load_odds(ODDS_CSV, initialized_db)

        # Try to overwrite with non-manual source
        overwrite_csv = tmp_path / "overwrite.csv"
        overwrite_csv.write_text("match_id,home_odds,away_odds,market_source\n2025R12PiesDons,5.00,1.10,auto_generated\n")
        load_odds(str(overwrite_csv), initialized_db)

        conn = get_connection(initialized_db)
        row = conn.execute("SELECT * FROM matches WHERE match_id = '2025R12PiesDons'").fetchone()
        conn.close()
        assert row["home_odds"] == 1.40  # Preserved manual odds

    def test_snapshot_always_created(self, initialized_db, tmp_path):
        """Even when match odds are preserved, snapshot should be created."""
        load_fixtures(FIXTURE_CSV, initialized_db)
        load_odds(ODDS_CSV, initialized_db)

        overwrite_csv = tmp_path / "snap.csv"
        overwrite_csv.write_text("match_id,home_odds,away_odds,market_source\n2025R12PiesDons,5.00,1.10,auto_gen\n")
        load_odds(str(overwrite_csv), initialized_db)

        conn = get_connection(initialized_db)
        snaps = conn.execute("SELECT * FROM odds_snapshots WHERE match_id = '2025R12PiesDons'").fetchall()
        conn.close()
        assert len(snaps) == 2  # Original + overwrite attempt


class TestLoadResults:
    def test_load_sample_results(self, initialized_db):
        load_fixtures(FIXTURE_CSV, initialized_db)
        count = load_results(RESULTS_CSV, initialized_db)
        assert count == 9

    def test_winner_calculated(self, initialized_db):
        load_fixtures(FIXTURE_CSV, initialized_db)
        load_results(RESULTS_CSV, initialized_db)
        conn = get_connection(initialized_db)
        row = conn.execute("SELECT * FROM matches WHERE match_id = '2025R12HawksBlues'").fetchone()
        conn.close()
        assert row["actual_winner"] == "home"
        assert row["home_score"] == 98
        assert row["away_score"] == 76
        assert row["actual_margin"] == 22
