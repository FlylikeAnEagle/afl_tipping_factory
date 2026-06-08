"""Tests for database schema creation."""

from src.db import init_db, get_connection


def test_init_db_creates_tables(initialized_db):
    """All four tables plus elo_ratings should exist."""
    conn = get_connection(initialized_db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "matches" in tables
    assert "predictions" in tables
    assert "odds_snapshots" in tables
    assert "match_features" in tables
    assert "elo_ratings" in tables


def test_init_db_idempotent(initialized_db):
    """Running init_db twice should not fail."""
    init_db(initialized_db)


def test_matches_columns(initialized_db):
    """Verify key columns exist in matches table."""
    conn = get_connection(initialized_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(matches)").fetchall()}
    conn.close()
    assert "match_id" in cols
    assert "bookie_favourite" in cols
    assert "implied_home_prob" in cols
    assert "elo_home_prob" in cols
    assert "actual_winner" in cols
    assert "market_source" in cols


def test_predictions_columns(initialized_db):
    """Verify key columns exist in predictions table."""
    conn = get_connection(initialized_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(predictions)").fetchall()}
    conn.close()
    assert "faded_favourite" in cols
    assert "fade_successful" in cols
    assert "was_correct" in cols
    assert "model_name" in cols
