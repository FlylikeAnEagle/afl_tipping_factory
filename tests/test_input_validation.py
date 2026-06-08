"""Tests for enhanced input validation in loaders."""

import os
import pytest
from src.loaders import load_fixtures, load_odds, load_results
from src.validation import validate_csv_crosscheck
from src.db import get_connection, init_db


BASE = os.path.join(os.path.dirname(__file__), "..")


class TestMissingColumns:
    def test_fixture_missing_columns(self, initialized_db, tmp_path):
        csv = tmp_path / "bad.csv"
        csv.write_text("match_id,home_team\n1,Collingwood\n")
        with pytest.raises(ValueError, match="missing required columns"):
            load_fixtures(str(csv), initialized_db)

    def test_odds_missing_columns(self, initialized_db, tmp_path):
        csv = tmp_path / "bad.csv"
        csv.write_text("match_id,home_odds\n1,1.50\n")
        with pytest.raises(ValueError, match="missing required columns"):
            load_odds(str(csv), initialized_db)

    def test_results_missing_columns(self, initialized_db, tmp_path):
        csv = tmp_path / "bad.csv"
        csv.write_text("match_id,home_score\n1,95\n")
        with pytest.raises(ValueError, match="missing required columns"):
            load_results(str(csv), initialized_db)

    def test_error_lists_found_vs_required(self, initialized_db, tmp_path):
        csv = tmp_path / "bad.csv"
        csv.write_text("match_id,home_team\n1,Collingwood\n")
        with pytest.raises(ValueError, match="Found:"):
            load_fixtures(str(csv), initialized_db)


class TestTeamNames:
    def test_unknown_team_warns(self, initialized_db, tmp_path, capsys):
        csv = tmp_path / "teams.csv"
        csv.write_text("match_id,season,round,home_team,away_team\nT1,2025,14,Foo,Bar\n")
        load_fixtures(str(csv), initialized_db)
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "Foo" in captured.out
        assert "not a recognized AFL team" in captured.out

    def test_valid_teams_no_warning(self, initialized_db, tmp_path, capsys):
        csv = tmp_path / "teams.csv"
        csv.write_text("match_id,season,round,home_team,away_team\nT1,2025,14,Collingwood,Essendon\n")
        load_fixtures(str(csv), initialized_db)
        captured = capsys.readouterr()
        assert "WARNING" not in captured.out

    def test_whitespace_stripped_from_teams(self, initialized_db, tmp_path, capsys):
        csv = tmp_path / "teams.csv"
        csv.write_text("match_id,season,round,home_team,away_team\nT1,2025,14, Collingwood , Essendon \n")
        load_fixtures(str(csv), initialized_db)
        captured = capsys.readouterr()
        assert "WARNING" not in captured.out
        conn = get_connection(initialized_db)
        row = conn.execute("SELECT home_team FROM matches WHERE match_id='T1'").fetchone()
        conn.close()
        assert row["home_team"] == "Collingwood"


class TestOddsValidation:
    def test_negative_odds_rejected(self, initialized_db, tmp_path):
        # Load fixture first
        fix = tmp_path / "fix.csv"
        fix.write_text("match_id,season,round,home_team,away_team\nT1,2025,14,Collingwood,Essendon\n")
        load_fixtures(str(fix), initialized_db)

        odds = tmp_path / "odds.csv"
        odds.write_text("match_id,home_odds,away_odds,market_source\nT1,-1.50,2.50,manual_test\n")
        with pytest.raises(ValueError, match="non-positive"):
            load_odds(str(odds), initialized_db)

    def test_zero_odds_rejected(self, initialized_db, tmp_path):
        fix = tmp_path / "fix.csv"
        fix.write_text("match_id,season,round,home_team,away_team\nT1,2025,14,Collingwood,Essendon\n")
        load_fixtures(str(fix), initialized_db)

        odds = tmp_path / "odds.csv"
        odds.write_text("match_id,home_odds,away_odds,market_source\nT1,0,2.50,manual_test\n")
        with pytest.raises(ValueError, match="non-positive"):
            load_odds(str(odds), initialized_db)

    def test_odds_match_id_mismatch(self, initialized_db, tmp_path):
        odds = tmp_path / "odds.csv"
        odds.write_text("match_id,home_odds,away_odds,market_source\nMISSING,1.50,2.50,manual_test\n")
        with pytest.raises(ValueError, match="no matching fixture"):
            load_odds(str(odds), initialized_db)


class TestResultsValidation:
    def test_results_before_predictions_rejected(self, initialized_db, tmp_path):
        """Cannot load results before predictions are recorded."""
        fix = tmp_path / "fix.csv"
        fix.write_text("match_id,season,round,home_team,away_team\nT1,2025,14,Collingwood,Essendon\n")
        load_fixtures(str(fix), initialized_db)

        results = tmp_path / "res.csv"
        results.write_text("match_id,home_score,away_score\nT1,95,80\n")
        with pytest.raises(ValueError, match="no predictions recorded"):
            load_results(str(results), initialized_db)

    def test_results_match_id_mismatch(self, initialized_db, tmp_path):
        results = tmp_path / "res.csv"
        results.write_text("match_id,home_score,away_score\nMISSING,95,80\n")
        with pytest.raises(ValueError, match="no matching fixture"):
            load_results(str(results), initialized_db)

    def test_negative_scores_rejected(self, initialized_db, tmp_path):
        results = tmp_path / "res.csv"
        results.write_text("match_id,home_score,away_score\nT1,-5,80\n")
        with pytest.raises(ValueError, match="negative scores"):
            load_results(str(results), initialized_db)


class TestDuplicateMatchIds:
    def test_duplicate_fixtures_rejected(self, initialized_db, tmp_path):
        csv = tmp_path / "dup.csv"
        csv.write_text("match_id,season,round,home_team,away_team\nT1,2025,14,Collingwood,Essendon\nT1,2025,14,Collingwood,Essendon\n")
        with pytest.raises(ValueError, match="duplicate match_id"):
            load_fixtures(str(csv), initialized_db)


class TestCSVCrosscheck:
    def test_missing_odds_detected(self, tmp_path):
        fix = tmp_path / "fix.csv"
        fix.write_text("match_id,season,round,home_team,away_team\nT1,2025,14,Collingwood,Essendon\nT2,2025,14,Hawthorn,Carlton\n")
        odds = tmp_path / "odds.csv"
        odds.write_text("match_id,home_odds,away_odds,market_source\nT1,1.50,2.50,manual_test\n")

        errors = validate_csv_crosscheck(str(fix), str(odds))
        assert any("no odds" in e for e in errors)

    def test_extra_odds_detected(self, tmp_path):
        fix = tmp_path / "fix.csv"
        fix.write_text("match_id,season,round,home_team,away_team\nT1,2025,14,Collingwood,Essendon\n")
        odds = tmp_path / "odds.csv"
        odds.write_text("match_id,home_odds,away_odds,market_source\nT1,1.50,2.50,manual_test\nT2,2.00,2.00,manual_test\n")

        errors = validate_csv_crosscheck(str(fix), str(odds))
        assert any("not in fixtures" in e for e in errors)

    def test_matching_passes(self, tmp_path):
        fix = tmp_path / "fix.csv"
        fix.write_text("match_id,season,round,home_team,away_team\nT1,2025,14,Collingwood,Essendon\n")
        odds = tmp_path / "odds.csv"
        odds.write_text("match_id,home_odds,away_odds,market_source\nT1,1.50,2.50,manual_test\n")

        errors = validate_csv_crosscheck(str(fix), str(odds))
        assert errors == []
