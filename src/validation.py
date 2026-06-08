"""Validation gate for AFL tipping factory."""

from .db import get_connection


class ValidationError(Exception):
    """Raised when validation fails."""


def validate_round(season: int, round_num: int, db_path: str | None = None) -> list[str]:
    """Validate data completeness for a round. Returns list of errors.
    Empty list means validation passed."""
    conn = get_connection(db_path)
    errors = []

    matches = conn.execute(
        "SELECT * FROM matches WHERE season = ? AND round = ?",
        (season, round_num),
    ).fetchall()

    if not matches:
        errors.append(f"No matches found for season={season} round={round_num}")
        conn.close()
        return errors

    for m in matches:
        mid = m["match_id"]

        # Check odds
        if m["home_odds"] is None or m["away_odds"] is None:
            errors.append(f"{mid}: missing odds (home_odds={m['home_odds']}, away_odds={m['away_odds']})")

        # Check implied probabilities
        if m["implied_home_prob"] is None or m["implied_away_prob"] is None:
            errors.append(f"{mid}: missing implied probabilities")

        # Check bookie favourite
        if m["bookie_favourite"] is None:
            errors.append(f"{mid}: missing bookie_favourite")

        # Check Elo probabilities (only for predictions)
        if m["elo_home_prob"] is None:
            errors.append(f"{mid}: missing Elo probabilities - run Elo model first")

        # Check features
        feat = conn.execute(
            "SELECT match_id FROM match_features WHERE match_id = ?", (mid,)
        ).fetchone()
        if not feat:
            errors.append(f"{mid}: missing feature row - run build_features first")

        # Check predictions exist
        preds = conn.execute(
            "SELECT model_name FROM predictions WHERE match_id = ?", (mid,)
        ).fetchall()
        if not preds:
            errors.append(f"{mid}: no predictions recorded")

    conn.close()
    return errors


def validate_results(season: int, round_num: int, db_path: str | None = None) -> list[str]:
    """Validate that results are complete for scoring."""
    conn = get_connection(db_path)
    errors = []

    matches = conn.execute(
        "SELECT * FROM matches WHERE season = ? AND round = ?",
        (season, round_num),
    ).fetchall()

    for m in matches:
        if m["actual_winner"] is None:
            errors.append(f"{m['match_id']}: missing actual_winner")
        if m["home_score"] is None or m["away_score"] is None:
            errors.append(f"{m['match_id']}: missing scores")

    conn.close()
    return errors
