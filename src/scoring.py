"""Scoring and fade tracking for AFL predictions."""

from .db import get_connection


def score_predictions(season: int, round_num: int, db_path: str | None = None) -> dict:
    """Score all predictions against actual results for a round.
    Returns summary dict with per-model scores."""
    conn = get_connection(db_path)

    matches = conn.execute(
        """SELECT m.match_id, m.home_team, m.away_team, m.actual_winner,
                  m.bookie_favourite
           FROM matches m
           WHERE m.season = ? AND m.round = ? AND m.actual_winner IS NOT NULL""",
        (season, round_num),
    ).fetchall()

    if not matches:
        conn.close()
        return {}

    models: dict[str, dict] = {}

    for m in matches:
        mid = m["match_id"]
        actual = m["actual_winner"]

        # Determine actual winner team name
        if actual == "home":
            actual_team = m["home_team"]
        elif actual == "away":
            actual_team = m["away_team"]
        else:
            actual_team = "draw"

        preds = conn.execute(
            "SELECT prediction_id, model_name, predicted_winner FROM predictions WHERE match_id = ?",
            (mid,),
        ).fetchall()

        for p in preds:
            model = p["model_name"]
            predicted = p["predicted_winner"]
            was_correct = 1 if predicted == actual_team else 0

            # Determine fade
            fav_team = m["home_team"] if m["bookie_favourite"] == "home" else m["away_team"] if m["bookie_favourite"] else None
            faded = 0
            fade_ok = None
            if fav_team and predicted != fav_team:
                faded = 1
                fade_ok = was_correct

            conn.execute(
                """UPDATE predictions SET
                   was_correct = ?, faded_favourite = ?, fade_successful = ?
                   WHERE prediction_id = ?""",
                (was_correct, faded, fade_ok, p["prediction_id"]),
            )

            if model not in models:
                models[model] = {"correct": 0, "total": 0, "fades": 0, "fade_wins": 0}
            models[model]["correct"] += was_correct
            models[model]["total"] += 1
            models[model]["fades"] += faded
            models[model]["fade_wins"] += (fade_ok or 0)

    conn.commit()
    conn.close()

    # Build summary
    summary = {}
    for model, stats in models.items():
        fade_rate = (
            round(stats["fade_wins"] / stats["fades"], 3)
            if stats["fades"] > 0
            else None  # NULL if no fades, not 0.0
        )
        summary[model] = {
            "correct": stats["correct"],
            "total": stats["total"],
            "strike_rate": round(stats["correct"] / stats["total"], 3) if stats["total"] else 0,
            "fades": stats["fades"],
            "fade_wins": stats["fade_wins"],
            "fade_success_rate": fade_rate,
        }
    return summary
