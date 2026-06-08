"""Test fixtures for AFL tipping factory tests."""

import os
import tempfile
import pytest

# Ensure src is importable
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary database path."""
    return str(tmp_path / "test_afl.db")


@pytest.fixture
def initialized_db(db_path):
    """Provide an initialized database."""
    from src.db import init_db
    conn = init_db(db_path)
    conn.close()
    return db_path


@pytest.fixture
def populated_db(initialized_db):
    """Provide a database with sample data loaded."""
    from src.loaders import load_fixtures, load_odds
    from src.probability import update_match_probabilities
    from src.elo import init_ratings, run_elo_predictions, record_bookie_predictions
    from src.features import build_features

    base = os.path.join(os.path.dirname(__file__), "..")
    fixture_csv = os.path.join(base, "data", "fixtures", "sample_round12_2025.csv")
    odds_csv = os.path.join(base, "data", "odds", "sample_round12_2025.csv")

    load_fixtures(fixture_csv, initialized_db)
    load_odds(odds_csv, initialized_db)
    update_match_probabilities(initialized_db)

    teams = [
        "Adelaide", "Brisbane", "Carlton", "Collingwood", "Essendon",
        "Fremantle", "Geelong", "Gold Coast", "GWS", "Hawthorn",
        "Melbourne", "North Melbourne", "Port Adelaide", "Richmond",
        "St Kilda", "Sydney", "West Coast", "Western Bulldogs",
    ]
    init_ratings(teams, initialized_db, 2025)
    run_elo_predictions(2025, 12, initialized_db)
    record_bookie_predictions(2025, 12, initialized_db)
    build_features(2025, 12, initialized_db)

    return initialized_db


@pytest.fixture
def scored_db(populated_db):
    """Provide a database with results loaded and scored."""
    from src.loaders import load_results
    from src.scoring import score_predictions
    from src.elo import update_ratings_from_results

    base = os.path.join(os.path.dirname(__file__), "..")
    results_csv = os.path.join(base, "data", "results", "sample_round12_2025.csv")

    load_results(results_csv, populated_db)
    score_predictions(2025, 12, populated_db)
    update_ratings_from_results(2025, 12, populated_db)

    return populated_db
