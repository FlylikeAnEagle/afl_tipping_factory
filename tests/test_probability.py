"""Tests for implied probability calculation."""

import pytest
from src.probability import implied_probabilities, calc_bookie_favourite, update_match_probabilities
from src.loaders import load_fixtures, load_odds


class TestImpliedProbabilities:
    def test_basic_calculation(self):
        hp, ap = implied_probabilities(2.0, 2.0)
        assert abs(hp - 0.5) < 0.001
        assert abs(ap - 0.5) < 0.001

    def test_overround_removal(self):
        hp, ap = implied_probabilities(1.50, 2.50)
        assert hp > ap  # Home favourite
        assert abs(hp + ap - 1.0) < 0.001  # Sum to 1

    def test_heavy_favourite(self):
        hp, ap = implied_probabilities(1.10, 8.00)
        assert hp > 0.85
        assert ap < 0.15
        assert abs(hp + ap - 1.0) < 0.001

    def test_invalid_odds(self):
        with pytest.raises(ValueError):
            implied_probabilities(0, 2.0)
        with pytest.raises(ValueError):
            implied_probabilities(-1, 2.0)

    def test_real_afl_odds(self):
        hp, ap = implied_probabilities(1.40, 2.90)
        assert hp > 0.60  # Collingwood strong favourite
        assert ap < 0.40


class TestBookieFavourite:
    def test_home_favourite(self):
        assert calc_bookie_favourite(0.65, 0.35) == "home"

    def test_away_favourite(self):
        assert calc_bookie_favourite(0.35, 0.65) == "away"

    def test_equal_odds(self):
        assert calc_bookie_favourite(0.50, 0.50) == "line"


class TestUpdateProbabilities:
    def test_updates_matches(self, initialized_db):
        import os
        base = os.path.join(os.path.dirname(__file__), "..")
        load_fixtures(os.path.join(base, "data", "fixtures", "sample_round12_2025.csv"), initialized_db)
        load_odds(os.path.join(base, "data", "odds", "sample_round12_2025.csv"), initialized_db)

        count = update_match_probabilities(initialized_db)
        assert count == 9

        from src.db import get_connection
        conn = get_connection(initialized_db)
        row = conn.execute("SELECT * FROM matches WHERE match_id = '2025R12PiesDons'").fetchone()
        conn.close()
        assert row["implied_home_prob"] is not None
        assert row["bookie_favourite"] == "home"
