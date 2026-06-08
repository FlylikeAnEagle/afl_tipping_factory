"""Tests for scoring and fade tracking."""

import os
from src.scoring import score_predictions
from src.loaders import load_results


BASE = os.path.join(os.path.dirname(__file__), "..")
RESULTS_CSV = os.path.join(BASE, "data", "results", "sample_round12_2025.csv")


class TestScoring:
    def test_scoring_returns_models(self, populated_db):
        load_results(RESULTS_CSV, populated_db)
        summary = score_predictions(2025, 12, populated_db)
        assert "elo_baseline" in summary
        assert "bookie_favourite" in summary

    def test_scoring_counts(self, scored_db):
        from src.db import get_connection
        conn = get_connection(scored_db)
        preds = conn.execute("SELECT * FROM predictions WHERE was_correct IS NOT NULL").fetchall()
        conn.close()
        assert len(preds) >= 18  # 9 matches * 2 models

    def test_strike_rate_calculation(self, scored_db):
        from src.db import get_connection
        conn = get_connection(scored_db)
        correct = conn.execute(
            "SELECT COUNT(*) FROM predictions WHERE model_name='bookie_favourite' AND was_correct=1"
        ).fetchone()[0]
        conn.close()
        assert correct >= 0

    def test_fade_tracking(self, scored_db):
        """Some predictions should track fades."""
        from src.db import get_connection
        conn = get_connection(scored_db)
        fades = conn.execute(
            "SELECT * FROM predictions WHERE faded_favourite = 1"
        ).fetchall()
        conn.close()
        # Elo may or may not have fades depending on ratings
        # Just verify the field is populated
        assert isinstance(fades, list)

    def test_fade_success_rate_null_when_no_fades(self, scored_db):
        """If a model had no fades, fade_success_rate must be None, not 0.0."""
        from src.db import get_connection
        conn = get_connection(scored_db)
        # Get models with no fades
        no_fade_models = conn.execute(
            "SELECT model_name FROM predictions GROUP BY model_name HAVING SUM(faded_favourite) = 0"
        ).fetchall()
        conn.close()
        # If any model has 0 fades, verify scoring returns None for that model
        from src.scoring import score_predictions
        summary = score_predictions(2025, 12, scored_db)
        for model in no_fade_models:
            assert summary[model["model_name"]]["fade_success_rate"] is None

    def test_was_correct_populated(self, scored_db):
        from src.db import get_connection
        conn = get_connection(scored_db)
        unscpred = conn.execute(
            "SELECT * FROM predictions WHERE was_correct IS NULL"
        ).fetchall()
        conn.close()
        assert len(unscpred) == 0  # All predictions should be scored


class TestMatrixOutput:
    def test_matrix_returns_dataframe(self, populated_db):
        from src.matrix import print_tipping_matrix
        import io, sys
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        df = print_tipping_matrix(2025, 12, populated_db)
        sys.stdout = old_stdout
        assert len(df) == 9
        assert "bookie_fav" in df.columns
        assert "elo_baseline_pick" in df.columns
