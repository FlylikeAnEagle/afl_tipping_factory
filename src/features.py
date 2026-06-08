"""AFL feature building for match_features table."""

from .db import get_connection


def build_features(season: int, round_num: int, db_path: str | None = None) -> int:
    """Build features for matches in a given round.
    v1: calculates rest days, ladder positions, recent form from matches data.
    Returns count of feature rows created."""
    conn = get_connection(db_path)

    matches = conn.execute(
        "SELECT match_id, home_team, away_team, match_date, venue, neutral_venue "
        "FROM matches WHERE season = ? AND round = ?",
        (season, round_num),
    ).fetchall()

    # Gather all match dates for rest day calculation
    all_matches = conn.execute(
        "SELECT match_id, home_team, away_team, match_date, season, round "
        "FROM matches WHERE season = ? ORDER BY match_date",
        (season,),
    ).fetchall()

    count = 0
    for m in matches:
        mid = m["match_id"]

        # Check if features already exist
        existing = conn.execute(
            "SELECT match_id FROM match_features WHERE match_id = ?", (mid,)
        ).fetchone()
        if existing:
            count += 1
            continue

        # Calculate rest days
        home_rest = _calc_rest_days(m["home_team"], m["match_date"], all_matches)
        away_rest = _calc_rest_days(m["away_team"], m["match_date"], all_matches)

        # Calculate ladder positions and form from previous rounds
        ladder = _calc_ladder(season, round_num, conn)
        home_pos = ladder.get(m["home_team"], {}).get("position")
        away_pos = ladder.get(m["away_team"], {}).get("position")
        home_pct = ladder.get(m["home_team"], {}).get("percentage")
        away_pct = ladder.get(m["away_team"], {}).get("percentage")

        # Recent form (last 3 matches win rate)
        home_form = _calc_form(m["home_team"], season, round_num, conn)
        away_form = _calc_form(m["away_team"], season, round_num, conn)

        # Short turnaround flag (< 7 days)
        short_home = 1 if home_rest is not None and home_rest < 7 else 0
        short_away = 1 if away_rest is not None and away_rest < 7 else 0

        conn.execute(
            """INSERT OR REPLACE INTO match_features
               (match_id, home_rest_days, away_rest_days, neutral_venue,
                home_ground_advantage, ladder_position_home, ladder_position_away,
                percentage_home, percentage_away, recent_form_home, recent_form_away,
                short_turnaround)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mid, home_rest, away_rest, m["neutral_venue"],
                0.0 if m["neutral_venue"] else 1.0,
                home_pos, away_pos, home_pct, away_pct,
                home_form, away_form,
                max(short_home, short_away),
            ),
        )
        count += 1

    conn.commit()
    conn.close()
    return count


def _calc_rest_days(team: str, match_date: str | None, all_matches: list) -> float | None:
    """Calculate rest days for a team before a given match."""
    if not match_date:
        return None
    prev_dates = [
        r["match_date"] for r in all_matches
        if r["match_date"] and r["match_date"] < match_date
        and (r["home_team"] == team or r["away_team"] == team)
    ]
    if not prev_dates:
        return None
    from datetime import datetime
    try:
        current = datetime.fromisoformat(match_date)
        last = datetime.fromisoformat(max(prev_dates))
        return (current - last).days
    except (ValueError, TypeError):
        return None


def _calc_ladder(season: int, before_round: int, conn) -> dict:
    """Calculate ladder positions up to (not including) a given round."""
    matches = conn.execute(
        """SELECT home_team, away_team, actual_winner, home_score, away_score
           FROM matches
           WHERE season = ? AND round < ? AND actual_winner IS NOT NULL""",
        (season, before_round),
    ).fetchall()

    teams: dict[str, dict] = {}
    for m in matches:
        ht, at = m["home_team"], m["away_team"]
        for t in (ht, at):
            if t not in teams:
                teams[t] = {"wins": 0, "played": 0, "for": 0, "against": 0}

        teams[ht]["played"] += 1
        teams[at]["played"] += 1
        teams[ht]["for"] += (m["home_score"] or 0)
        teams[ht]["against"] += (m["away_score"] or 0)
        teams[at]["for"] += (m["away_score"] or 0)
        teams[at]["against"] += (m["home_score"] or 0)

        if m["actual_winner"] == "home":
            teams[ht]["wins"] += 1
        elif m["actual_winner"] == "away":
            teams[at]["wins"] += 1

    # Sort by wins, then percentage
    ladder = {}
    sorted_teams = sorted(
        teams.items(),
        key=lambda x: (x[1]["wins"], x[1]["for"] / max(x[1]["against"], 1)),
        reverse=True,
    )
    for i, (team, stats) in enumerate(sorted_teams, 1):
        pct = round(stats["for"] / max(stats["against"], 1) * 100, 1) if stats["against"] else None
        ladder[team] = {"position": i, "percentage": pct}
    return ladder


def _calc_form(team: str, season: int, before_round: int, conn) -> float | None:
    """Calculate recent form (win rate) over last 3 matches."""
    matches = conn.execute(
        """SELECT home_team, away_team, actual_winner, round
           FROM matches
           WHERE season = ? AND round < ? AND actual_winner IS NOT NULL
             AND (home_team = ? OR away_team = ?)
           ORDER BY round DESC LIMIT 3""",
        (season, before_round, team, team),
    ).fetchall()

    if not matches:
        return None
    wins = sum(
        1 for m in matches
        if (m["actual_winner"] == "home" and m["home_team"] == team)
        or (m["actual_winner"] == "away" and m["away_team"] == team)
    )
    return round(wins / len(matches), 3)
