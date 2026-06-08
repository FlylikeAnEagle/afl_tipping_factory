"""CSV loaders for AFL fixtures, odds, and results."""

import pandas as pd
from pathlib import Path
from .db import get_connection

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_fixtures(csv_path: str | Path, db_path: str | None = None) -> int:
    """Load AFL fixture CSV into matches table. Returns rows inserted."""
    df = pd.read_csv(csv_path)
    required = {"match_id", "season", "round", "home_team", "away_team"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Fixture CSV missing columns: {missing}")

    conn = get_connection(db_path)
    count = 0
    for _, row in df.iterrows():
        try:
            conn.execute(
                """INSERT OR IGNORE INTO matches
                   (match_id, season, round, match_date, kickoff_time, venue,
                    neutral_venue, home_team, away_team)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(row["match_id"]),
                    int(row["season"]),
                    int(row["round"]),
                    row.get("match_date"),
                    row.get("kickoff_time"),
                    row.get("venue"),
                    int(row.get("neutral_venue", 0)),
                    str(row["home_team"]),
                    str(row["away_team"]),
                ),
            )
            count += 1
        except Exception as e:
            conn.close()
            raise RuntimeError(f"Insert failed for match {row['match_id']}: {e}")
    conn.commit()
    conn.close()
    return count


def load_odds(csv_path: str | Path, db_path: str | None = None) -> int:
    """Load odds CSV. Updates matches and inserts into odds_snapshots.
    Never overwrites existing manual odds unless force=True via snapshot."""
    df = pd.read_csv(csv_path)
    required = {"match_id", "home_odds", "away_odds", "market_source"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Odds CSV missing columns: {missing}")

    conn = get_connection(db_path)
    count = 0
    for _, row in df.iterrows():
        mid = str(row["match_id"])
        source = str(row["market_source"])

        # Insert snapshot (always preserve raw odds)
        conn.execute(
            """INSERT INTO odds_snapshots (match_id, home_odds, away_odds, market_source)
               VALUES (?, ?, ?, ?)""",
            (mid, float(row["home_odds"]), float(row["away_odds"]), source),
        )

        # Update matches odds - preserve existing manual odds
        existing = conn.execute(
            "SELECT market_source FROM matches WHERE match_id = ?", (mid,)
        ).fetchone()
        if existing and existing["market_source"]:
            if str(existing["market_source"]).startswith("manual_") and not source.startswith("manual_"):
                continue  # Don't overwrite manual odds with non-manual

        conn.execute(
            """UPDATE matches SET
               home_odds = ?, away_odds = ?, market_source = ?,
               market_last_update = datetime('now')
               WHERE match_id = ?""",
            (float(row["home_odds"]), float(row["away_odds"]), source, mid),
        )
        count += 1
    conn.commit()
    conn.close()
    return count


def load_results(csv_path: str | Path, db_path: str | None = None) -> int:
    """Load results CSV. Updates matches with actual scores and winner."""
    df = pd.read_csv(csv_path)
    required = {"match_id", "home_score", "away_score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Results CSV missing columns: {missing}")

    conn = get_connection(db_path)
    count = 0
    for _, row in df.iterrows():
        mid = str(row["match_id"])
        hs = int(row["home_score"])
        as_ = int(row["away_score"])
        winner = "home" if hs > as_ else ("away" if as_ > hs else "draw")
        margin = abs(hs - as_)

        conn.execute(
            """UPDATE matches SET
               actual_winner = ?, home_score = ?, away_score = ?, actual_margin = ?
               WHERE match_id = ?""",
            (winner, hs, as_, margin, mid),
        )
        count += 1
    conn.commit()
    conn.close()
    return count
