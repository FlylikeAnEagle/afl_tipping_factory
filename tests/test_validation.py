"""Tests for validation gate."""

import os
from src.validation import validate_round, validate_results
from src.loaders import load_fixtures, load_odds, load_results


BASE = os.path.join(os.path.dirname(__file__), "..")
FIXTURE_CSV = os.path.join(BASE, "data", "fixtures", "sample_round12_2025.csv")
ODDS_CSV = os.path.join(BASE, "data", "odds", "sample_round12_2025.csv")
RESULTS_CSV = os.path.join(BASE, "data", "results", "sample_round12_2025.csv")


class TestValidateRound:
    def test_no_matches_fails(self, initialized_db):
        errors = validate_round(2025, 12, initialized_db)
        assert len(errors) > 0
        assert "No matches" in errors[0]

    def test_missing_odds_fails(self, initialized_db):
        load_fixtures(FIXTURE_CSV, initialized_db)
        errors = validate_round(2025, 12, initialized_db)
        assert any("missing odds" in e for e in errors)

    def test_full_data_passes(self, populated_db):
        errors = validate_round(2025, 12, populated_db)
        assert errors == [], f"Validation errors: {errors}"


class TestValidateResults:
    def test_no_results_fails(self, populated_db):
        errors = validate_results(2025, 12, populated_db)
        assert len(errors) > 0

    def test_complete_results_pass(self, populated_db):
        load_results(RESULTS_CSV, populated_db)
        errors = validate_results(2025, 12, populated_db)
        assert errors == []
