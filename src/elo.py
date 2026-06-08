"""Elo rating system for AFL with home ground advantage."""

import math
from .db import get_connection

DEFAULT_K = 32
DEFAULT_HGA = 50  # Home ground advantage in Elo points
INITIAL_RATING = 1500.0
MARGIN_FACTOR = 0.03  # Multiplier for margin-based K adjustment


def expected_score(rating_a: float, rating_b: float) -> float:
    """Expected score (probability) for team A vs team B."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def elo_update(
    rating_a: float, rating_b: float, outcome: float,
    k: float = DEFAULT_K, margin: int = 0,
) -> tuple[float, float]:
    """Update Elo ratings after a match.
    outcome: 1.0 for A win, 0.0 for B win, 0.5 for draw.
    margin-based K scaling for AFL."""
    k_adj = k * (1.0 + MARGIN_FACTOR * margin) if margin > 0 else k
    ea = expected_score(rating_a, rating_b)
    eb = expected_score(rating_b, rating_a)
    new_a = rating_a + k_adj * (outcome - ea)
    new_b = rating_b + k_adj * ((1.0 - outcome) - eb)
    return round(new_a, 2), round(new_b, 2)


def init_ratings(teams: list[str], db_path: str | None = None, season: int = 2025) -> None:
    """Initialize Elo ratings for a list of teams."""
    conn = get_connection(db_path)
    for team in teams:
        conn.execute(
            "INSERT OR IGNORE INTO elo_ratings (team, rating, season) VALUES (?, ?, ?)",
            (team, INITIAL_RATING, season),
        )
    conn.commit()
    conn.close()


def get_ratings(db_path: str | None = None) -> dict[str, float]:
    """Return current Elo ratings as {team: rating}."""
    conn = get_connection(db_path)
    rows = conn.execute("SELECT team, rating FROM elo_ratings").fetchall()
    conn.close()
    return {r["team"]: r["rating"] for r in rows}


def predict_match(
    home_rating: float, away_rating: float, neutral: bool = False,
    hga: float = DEFAULT_HGA,
) -> tuple[float, float, float, float]:
    """Predict a match. Returns (home_prob, away_prob, expected_margin, margin_sd)."""
    hga_adj = 0.0 if neutral else hga
    home_effective = home_rating + hga_adj
    home_prob = expected_score(home_effective, away_rating)
    away_prob = 1.0 - home_prob

    # Approximate expected margin from probability differential
    expected_margin = round((home_prob - 0.5) * 100, 1)  # rough AFL scaling
    margin_sd = 36.0  # typical AFL margin standard deviation

    return round(home_prob, 4), round(away_prob, 4), expected_margin, margin_sd


def update_ratings_from_results(season: int, round_num: int, db_path: str | None = None) -> int:
    """Update Elo ratings based on completed matches for a given season/round.
    Returns count of matches processed."""
    conn = get_connection(db_path)
    matches = conn.execute(
        """SELECT match_id, home_team, away_team, actual_winner, actual_margin,
                  neutral_venue
           FROM matches
           WHERE season = ? AND round = ? AND actual_winner IS NOT NULL""",
        (season, round_num),
    ).fetchall()

    ratings = get_ratings(db_path)
    count = 0
    for m in matches:
        ht, at = m["home_team"], m["away_team"]
        if ht not in ratings:
            ratings[ht] = INITIAL_RATING
        if at not in ratings:
            ratings[at] = INITIAL_RATING

        if m["actual_winner"] == "home":
            outcome = 1.0
        elif m["actual_winner"] == "away":
            outcome = 0.0
        else:
            outcome = 0.5

        margin = m["actual_margin"] or 0
        new_h, new_a = elo_update(ratings[ht], ratings[at], outcome, margin=margin)
        ratings[ht] = new_h
        ratings[at] = new_a

        # Persist ratings
        conn.execute(
            "INSERT OR REPLACE INTO elo_ratings (team, rating, season) VALUES (?, ?, ?)",
            (ht, new_h, season),
        )
        conn.execute(
            "INSERT OR REPLACE INTO elo_ratings (team, rating, season) VALUES (?, ?, ?)",
            (at, new_a, season),
        )
        count += 1

    conn.commit()
    conn.close()
    return count


def run_elo_predictions(season: int, round_num: int, db_path: str | None = None) -> int:
    """Run Elo predictions for unplayed matches. Updates matches table and
    records predictions. Returns count of predictions made."""
    conn = get_connection(db_path)
    ratings = get_ratings(db_path)

    matches = conn.execute(
        """SELECT match_id, home_team, away_team, neutral_venue
           FROM matches
           WHERE season = ? AND round = ? AND actual_winner IS NULL""",
        (season, round_num),
    ).fetchall()

    count = 0
    for m in matches:
        ht, at = m["home_team"], m["away_team"]
        hr = ratings.get(ht, INITIAL_RATING)
        ar = ratings.get(at, INITIAL_RATING)
        neutral = bool(m["neutral_venue"])

        hp, ap, exp_margin, margin_sd = predict_match(hr, ar, neutral)
        predicted = ht if hp > ap else at

        # Update match Elo fields
        conn.execute(
            """UPDATE matches SET
               elo_expected_margin = ?, elo_margin_sd = ?,
               elo_home_prob = ?, elo_away_prob = ?
               WHERE match_id = ?""",
            (exp_margin, margin_sd, hp, ap, m["match_id"]),
        )

        # Record prediction
        confidence = abs(hp - ap)
        if confidence < 0.05:
            cr = "low"
        elif confidence < 0.15:
            cr = "medium"
        else:
            cr = "high"

        conn.execute(
            """INSERT OR IGNORE INTO predictions
               (match_id, model_name, predicted_winner, predicted_home_prob,
                predicted_away_prob, confidence_score, confidence_rating)
               VALUES (?, 'elo_baseline', ?, ?, ?, ?, ?)""",
            (m["match_id"], predicted, hp, ap, confidence, cr),
        )
        count += 1

    conn.commit()
    conn.close()
    return count


def record_bookie_predictions(season: int, round_num: int, db_path: str | None = None) -> int:
    """Record bookie favourite predictions for comparison baseline."""
    conn = get_connection(db_path)

    matches = conn.execute(
        """SELECT match_id, home_team, away_team, bookie_favourite,
                  implied_home_prob, implied_away_prob
           FROM matches
           WHERE season = ? AND round = ?
             AND bookie_favourite IS NOT NULL
             AND actual_winner IS NULL""",
        (season, round_num),
    ).fetchall()

    count = 0
    for m in matches:
        fav = m["bookie_favourite"]
        predicted = m["home_team"] if fav == "home" else m["away_team"]
        hp = m["implied_home_prob"]
        ap = m["implied_away_prob"]

        conn.execute(
            """INSERT OR IGNORE INTO predictions
               (match_id, model_name, predicted_winner, predicted_home_prob,
                predicted_away_prob, confidence_score, confidence_rating)
               VALUES (?, 'bookie_favourite', ?, ?, ?, ?, 'high')""",
            (m["match_id"], predicted, hp, ap, abs((hp or 0) - (ap or 0))),
        )
        count += 1

    conn.commit()
    conn.close()
    return count
