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
            errors.append(f"{mid}: missing odds — load odds CSV before running pre-round")

        # Check implied probabilities
        if m["implied_home_prob"] is None or m["implied_away_prob"] is None:
            errors.append(f"{mid}: missing implied probabilities — run probability calculation first")

        # Check bookie favourite
        if m["bookie_favourite"] is None:
            errors.append(f"{mid}: missing bookie_favourite — run probability calculation first")

        # Check Elo probabilities
        if m["elo_home_prob"] is None:
            errors.append(f"{mid}: missing Elo probabilities — run Elo model first")

        # Check features
        feat = conn.execute(
            "SELECT match_id FROM match_features WHERE match_id = ?", (mid,)
        ).fetchone()
        if not feat:
            errors.append(f"{mid}: missing feature row — run build_features first")

        # Check predictions exist
        preds = conn.execute(
            "SELECT model_name FROM predictions WHERE match_id = ?", (mid,)
        ).fetchall()
        if not preds:
            errors.append(f"{mid}: no predictions recorded — run Elo and bookie prediction models first")

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
            errors.append(f"{m['match_id']}: missing actual_winner — load results CSV first")
        if m["home_score"] is None or m["away_score"] is None:
            errors.append(f"{m['match_id']}: missing scores — load results CSV first")

    conn.close()
    return errors


def validate_csv_crosscheck(fixture_path: str, odds_path: str | None = None) -> list[str]:
    """Cross-check fixture and odds CSVs for consistency before loading.
    Returns list of warnings/errors."""
    import pandas as pd

    errors = []

    fix_df = pd.read_csv(fixture_path)
    for col in fix_df.select_dtypes(include="str").columns:
        fix_df[col] = fix_df[col].str.strip()
    fix_ids = set(fix_df["match_id"].astype(str))
    fix_teams = set(fix_df["home_team"].astype(str)) | set(fix_df["away_team"].astype(str))

    if odds_path:
        odds_df = pd.read_csv(odds_path)
        for col in odds_df.select_dtypes(include="str").columns:
            odds_df[col] = odds_df[col].str.strip()
        odds_ids = set(odds_df["match_id"].astype(str))

        # Check match_id coverage
        missing_odds = fix_ids - odds_ids
        if missing_odds:
            errors.append(
                f"Fixtures have {len(missing_odds)} match(es) with no odds:\n"
                f"  {sorted(missing_odds)}\n"
                f"  Add odds for these matches before running pre-round."
            )

        extra_odds = odds_ids - fix_ids
        if extra_odds:
            errors.append(
                f"Odds CSV has {len(extra_odds)} match(es) not in fixtures:\n"
                f"  {sorted(extra_odds)}"
            )

    return errors
