"""Tipping matrix output for AFL predictions."""

import pandas as pd
from .db import get_connection


def print_tipping_matrix(season: int, round_num: int, db_path: str | None = None) -> pd.DataFrame:
    """Generate and print a tipping matrix for a round.
    Returns DataFrame with columns: match, teams, bookie_fav, elo_pick, elo_conf, ..."""
    conn = get_connection(db_path)

    matches = conn.execute(
        """SELECT match_id, home_team, away_team, venue, bookie_favourite,
                  implied_home_prob, implied_away_prob,
                  elo_home_prob, elo_away_prob
           FROM matches
           WHERE season = ? AND round = ?
           ORDER BY match_date, kickoff_time""",
        (season, round_num),
    ).fetchall()

    rows = []
    for m in matches:
        row = {
            "match_id": m["match_id"],
            "home": m["home_team"],
            "away": m["away_team"],
            "venue": m["venue"],
            "bookie_fav": m["home_team"] if m["bookie_favourite"] == "home"
            else (m["away_team"] if m["bookie_favourite"] == "away" else "line"),
            "implied_home": m["implied_home_prob"],
            "implied_away": m["implied_away_prob"],
        }

        # Get all predictions for this match
        preds = conn.execute(
            "SELECT model_name, predicted_winner, confidence_score, confidence_rating "
            "FROM predictions WHERE match_id = ?",
            (m["match_id"],),
        ).fetchall()

        for p in preds:
            row[f"{p['model_name']}_pick"] = p["predicted_winner"]
            row[f"{p['model_name']}_conf"] = p["confidence_score"]
            row[f"{p['model_name']}_rating"] = p["confidence_rating"]

        rows.append(row)

    conn.close()
    df = pd.DataFrame(rows)

    if not df.empty:
        print(f"\n=== AFL TIPPING MATRIX — Season {season} Round {round_num} ===\n")
        cols = ["match_id", "home", "away", "venue", "bookie_fav"]
        # Add model columns dynamically
        model_cols = [c for c in df.columns if c not in cols and "implied" not in c]
        display_cols = cols + model_cols
        # Only show columns that exist
        display_cols = [c for c in display_cols if c in df.columns]
        print(df[display_cols].to_string(index=False))
        print()

    return df
