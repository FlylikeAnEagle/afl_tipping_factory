"""Convenience script to run the full AFL tipping pipeline."""

from .db import init_db
from .loaders import load_fixtures, load_odds, load_results
from .probability import update_match_probabilities
from .elo import init_ratings, run_elo_predictions, record_bookie_predictions, update_ratings_from_results
from .features import build_features
from .validation import validate_round, validate_results
from .matrix import print_tipping_matrix
from .scoring import score_predictions


def run_pre_round(fixture_csv: str, odds_csv: str, season: int, round_num: int,
                  teams: list[str] | None = None, db_path: str | None = None) -> None:
    """Full pre-round pipeline: load fixtures + odds, calc probs, run Elo, validate, print matrix."""
    conn = init_db(db_path)

    # Load data
    n_fix = load_fixtures(fixture_csv, db_path)
    n_odds = load_odds(odds_csv, db_path)
    print(f"Loaded {n_fix} fixtures, {n_odds} odds entries")

    # Calculate probabilities
    n_prob = update_match_probabilities(db_path)
    print(f"Updated {n_prob} implied probabilities")

    # Init ratings if needed
    if teams:
        init_ratings(teams, db_path, season)

    # Run models
    n_elo = run_elo_predictions(season, round_num, db_path)
    n_bookie = record_bookie_predictions(season, round_num, db_path)
    print(f"Elo: {n_elo} predictions, Bookie: {n_bookie} predictions")

    # Build features
    n_feat = build_features(season, round_num, db_path)
    print(f"Built {n_feat} feature rows")

    # Validate
    errors = validate_round(season, round_num, db_path)
    if errors:
        print(f"\nVALIDATION ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        raise SystemExit(1)

    print("\nValidation passed.")
    matrix = print_tipping_matrix(season, round_num, db_path)
    conn.close()


def run_post_round(results_csv: str, season: int, round_num: int,
                   db_path: str | None = None) -> dict:
    """Post-round pipeline: load results, score predictions, update Elo."""
    conn = init_db(db_path)

    # Validate we can score
    pre_errors = validate_round(season, round_num, db_path)
    if pre_errors:
        print(f"Pre-result validation issues: {len(pre_errors)}")
        for e in pre_errors:
            print(f"  - {e}")

    # Load results
    n_res = load_results(results_csv, db_path)
    print(f"Loaded {n_res} results")

    # Validate results completeness
    res_errors = validate_results(season, round_num, db_path)
    if res_errors:
        print(f"\nRESULT VALIDATION ERRORS ({len(res_errors)}):")
        for e in res_errors:
            print(f"  - {e}")
        raise SystemExit(1)

    # Score predictions
    summary = score_predictions(season, round_num, db_path)

    # Update Elo
    n_elo = update_ratings_from_results(season, round_num, db_path)
    print(f"Updated Elo ratings from {n_elo} matches")

    # Print summary
    print(f"\n=== SCORING SUMMARY — Season {season} Round {round_num} ===\n")
    for model, stats in summary.items():
        fade_str = f"{stats['fade_success_rate']:.1%}" if stats['fade_success_rate'] is not None else "N/A"
        print(f"  {model}: {stats['correct']}/{stats['total']} ({stats['strike_rate']:.1%}) "
              f"| Fades: {stats['fades']} wins {stats['fade_wins']} ({fade_str})")

    conn.close()
    return summary
