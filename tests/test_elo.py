"""Tests for Elo rating system."""

from src.elo import (
    expected_score, elo_update, init_ratings, get_ratings,
    predict_match, run_elo_predictions, record_bookie_predictions,
    update_ratings_from_results,
)
from src.db import get_connection


class TestEloMath:
    def test_expected_score_equal(self):
        e = expected_score(1500, 1500)
        assert abs(e - 0.5) < 0.001

    def test_expected_score_home_advantage(self):
        e = expected_score(1600, 1500)
        assert e > 0.5

    def test_elo_update_home_win(self):
        new_h, new_a = elo_update(1500, 1500, 1.0)
        assert new_h > 1500
        assert new_a < 1500

    def test_elo_update_draw(self):
        new_h, new_a = elo_update(1500, 1500, 0.5)
        assert abs(new_h - 1500) < 0.01
        assert abs(new_a - 1500) < 0.01

    def test_margin_scales_k(self):
        _, _ = elo_update(1500, 1500, 1.0, margin=50)
        new_h_big, _ = elo_update(1500, 1500, 1.0, margin=50)
        new_h_small, _ = elo_update(1500, 1500, 1.0, margin=5)
        assert new_h_big > new_h_small  # Bigger margin = bigger update


class TestPredictMatch:
    def test_equal_teams_neutral(self):
        hp, ap, margin, sd = predict_match(1500, 1500, neutral=True)
        assert abs(hp - 0.5) < 0.001
        assert abs(ap - 0.5) < 0.001

    def test_home_advantage(self):
        hp_neutral, _, _, _ = predict_match(1500, 1500, neutral=True)
        hp_home, _, _, _ = predict_match(1500, 1500, neutral=False)
        assert hp_home > hp_neutral


class TestRatings:
    def test_init_and_get(self, initialized_db):
        teams = ["Collingwood", "Carlton", "Essendon"]
        init_ratings(teams, initialized_db, 2025)
        ratings = get_ratings(initialized_db)
        assert ratings["Collingwood"] == 1500.0
        assert len(ratings) == 3

    def test_ratings_update(self, populated_db):
        from src.loaders import load_results
        import os
        results_csv = os.path.join(os.path.dirname(__file__), "..", "data", "results", "sample_round12_2025.csv")
        load_results(results_csv, populated_db)
        count = update_ratings_from_results(2025, 12, populated_db)
        assert count == 9

        ratings = get_ratings(populated_db)
        # Some teams should have changed from 1500
        assert any(v != 1500.0 for v in ratings.values())


class TestPredictions:
    def test_elo_predictions_created(self, populated_db):
        conn = get_connection(populated_db)
        preds = conn.execute(
            "SELECT * FROM predictions WHERE model_name = 'elo_baseline'"
        ).fetchall()
        conn.close()
        assert len(preds) == 9

    def test_bookie_predictions_created(self, populated_db):
        conn = get_connection(populated_db)
        preds = conn.execute(
            "SELECT * FROM predictions WHERE model_name = 'bookie_favourite'"
        ).fetchall()
        conn.close()
        assert len(preds) == 9

    def test_elo_updates_match_table(self, populated_db):
        conn = get_connection(populated_db)
        row = conn.execute(
            "SELECT elo_home_prob, elo_away_prob FROM matches WHERE match_id = '2025R12PiesDons'"
        ).fetchone()
        conn.close()
        assert row["elo_home_prob"] is not None
        assert row["elo_away_prob"] is not None
