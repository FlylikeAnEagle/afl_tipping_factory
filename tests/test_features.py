"""Tests for feature building."""

from src.features import build_features
from src.db import get_connection


class TestFeatures:
    def test_features_created(self, populated_db):
        conn = get_connection(populated_db)
        features = conn.execute("SELECT * FROM match_features").fetchall()
        conn.close()
        assert len(features) == 9

    def test_feature_fields(self, populated_db):
        conn = get_connection(populated_db)
        row = conn.execute(
            "SELECT * FROM match_features WHERE match_id = '2025R12PiesDons'"
        ).fetchone()
        conn.close()
        assert row["neutral_venue"] == 0
        assert row["home_ground_advantage"] == 1.0

    def test_features_idempotent(self, populated_db):
        count1 = build_features(2025, 12, populated_db)
        count2 = build_features(2025, 12, populated_db)
        assert count1 == count2 == 9
