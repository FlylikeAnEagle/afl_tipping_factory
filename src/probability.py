"""Implied probability calculation with overround removal."""

from .db import get_connection


def implied_probabilities(home_odds: float, away_odds: float) -> tuple[float, float]:
    """Calculate implied probabilities with overround removal (normalization).
    Returns (home_prob, away_prob) summing to ~1.0."""
    if home_odds <= 0 or away_odds <= 0:
        raise ValueError(f"Odds must be positive: home={home_odds}, away={away_odds}")

    raw_home = 1.0 / home_odds
    raw_away = 1.0 / away_odds
    overround = raw_home + raw_away  # >1.0 means bookie margin

    home_prob = raw_home / overround
    away_prob = raw_away / overround
    return round(home_prob, 4), round(away_prob, 4)


def calc_bookie_favourite(home_prob: float, away_prob: float) -> str:
    """Return 'home', 'away', or 'line' if equal."""
    if home_prob > away_prob:
        return "home"
    elif away_prob > home_prob:
        return "away"
    return "line"


def update_match_probabilities(db_path: str | None = None) -> int:
    """Calculate and store implied probabilities for all matches with odds.
    Returns count of matches updated."""
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT match_id, home_odds, away_odds FROM matches WHERE home_odds IS NOT NULL AND away_odds IS NOT NULL"
    ).fetchall()

    count = 0
    for row in rows:
        hp, ap = implied_probabilities(row["home_odds"], row["away_odds"])
        fav = calc_bookie_favourite(hp, ap)
        conn.execute(
            """UPDATE matches SET
               implied_home_prob = ?, implied_away_prob = ?, bookie_favourite = ?
               WHERE match_id = ?""",
            (hp, ap, fav, row["match_id"]),
        )
        count += 1
    conn.commit()
    conn.close()
    return count
