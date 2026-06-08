"""CSV loaders for AFL fixtures, odds, and results."""

import pandas as pd
from pathlib import Path
from .db import get_connection

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

VALID_TEAMS = {
    "Adelaide", "Brisbane", "Carlton", "Collingwood", "Essendon",
    "Fremantle", "Geelong", "Gold Coast", "GWS", "Hawthorn",
    "Melbourne", "North Melbourne", "Port Adelaide", "Richmond",
    "St Kilda", "Sydney", "West Coast", "Western Bulldogs",
}


def _validate_columns(df: pd.DataFrame, required: set, csv_name: str) -> None:
    """Raise with friendly message if required columns missing."""
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"{csv_name} CSV missing required columns: {', '.join(sorted(missing))}\n"
            f"  Found: {', '.join(sorted(df.columns))}\n"
            f"  Required: {', '.join(sorted(required))}"
        )


def _validate_team_names(df: pd.DataFrame, team_cols: list[str], csv_name: str) -> list[str]:
    """Return list of warnings for unrecognized team names."""
    warnings = []
    for col in team_cols:
        if col in df.columns:
            for val in df[col].unique():
                val_str = str(val).strip()
                if val_str and val_str not in VALID_TEAMS:
                    warnings.append(
                        f"{csv_name}: '{val_str}' in column '{col}' is not a recognized AFL team.\n"
                        f"  Valid teams: {', '.join(sorted(VALID_TEAMS))}"
                    )
    return warnings


def load_fixtures(csv_path: str | Path, db_path: str | None = None) -> int:
    """Load AFL fixture CSV into matches table. Returns rows inserted."""
    df = pd.read_csv(csv_path)
    # Strip whitespace from string columns
    for col in df.select_dtypes(include="str").columns:
        df[col] = df[col].str.strip()

    required = {"match_id", "season", "round", "home_team", "away_team"}
    _validate_columns(df, required, "Fixture")

    # Validate team names
    warnings = _validate_team_names(df, ["home_team", "away_team"], "Fixture")
    for w in warnings:
        print(f"WARNING: {w}")

    # Check for duplicate match_ids
    dupes = df[df.duplicated(subset=["match_id"], keep=False)]
    if not dupes.empty:
        raise ValueError(
            f"Fixture CSV has duplicate match_id values: {dupes['match_id'].unique().tolist()}"
        )

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
                    row.get("match_date") or None,
                    row.get("kickoff_time") or None,
                    row.get("venue") or None,
                    int(row.get("neutral_venue", 0) or 0),
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
    for col in df.select_dtypes(include="str").columns:
        df[col] = df[col].str.strip()

    required = {"match_id", "home_odds", "away_odds", "market_source"}
    _validate_columns(df, required, "Odds")

    # Validate odds are positive numbers
    for col in ["home_odds", "away_odds"]:
        if (df[col] <= 0).any():
            bad = df[df[col] <= 0]
            raise ValueError(
                f"Odds CSV has non-positive values in '{col}':\n"
                f"  match_ids: {bad['match_id'].tolist()}\n"
                f"  Odds must be > 0 (decimal format, e.g. 2.10)"
            )

    conn = get_connection(db_path)

    # Check that match_ids exist in fixtures
    existing = {r[0] for r in conn.execute("SELECT match_id FROM matches").fetchall()}
    csv_ids = set(df["match_id"].astype(str))
    missing_fixtures = csv_ids - existing
    if missing_fixtures:
        conn.close()
        raise ValueError(
            f"Odds CSV contains match_ids with no matching fixture:\n"
            f"  {sorted(missing_fixtures)}\n"
            f"  Load fixtures first using: load_fixtures()"
        )

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
        existing_row = conn.execute(
            "SELECT market_source FROM matches WHERE match_id = ?", (mid,)
        ).fetchone()
        if existing_row and existing_row["market_source"]:
            if str(existing_row["market_source"]).startswith("manual_") and not source.startswith("manual_"):
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
    """Load results CSV. Updates matches with actual scores and winner.
    Validates that predictions exist before loading results."""
    df = pd.read_csv(csv_path)
    for col in df.select_dtypes(include="str").columns:
        df[col] = df[col].str.strip()

    required = {"match_id", "home_score", "away_score"}
    _validate_columns(df, required, "Results")

    # Validate scores are non-negative integers
    for col in ["home_score", "away_score"]:
        if (df[col] < 0).any():
            bad = df[df[col] < 0]
            raise ValueError(
                f"Results CSV has negative scores in '{col}':\n"
                f"  match_ids: {bad['match_id'].tolist()}"
            )

    conn = get_connection(db_path)

    # Check that match_ids exist
    existing = {r[0] for r in conn.execute("SELECT match_id FROM matches").fetchall()}
    csv_ids = set(df["match_id"].astype(str))
    missing_fixtures = csv_ids - existing
    if missing_fixtures:
        conn.close()
        raise ValueError(
            f"Results CSV contains match_ids with no matching fixture:\n"
            f"  {sorted(missing_fixtures)}\n"
            f"  Load fixtures first using: load_fixtures()"
        )

    # Check that predictions exist before loading results
    no_pred_matches = []
    for mid in csv_ids:
        preds = conn.execute(
            "SELECT prediction_id FROM predictions WHERE match_id = ?", (mid,)
        ).fetchall()
        if not preds:
            no_pred_matches.append(mid)

    if no_pred_matches:
        conn.close()
        raise ValueError(
            f"Results cannot be loaded — no predictions recorded for:\n"
            f"  {sorted(no_pred_matches)}\n"
            f"  Run pre-round pipeline first to record predictions before loading results."
        )

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
