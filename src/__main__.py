"""CLI entrypoint: python -m src [pre-round|post-round|matrix|init-db] --season Y --round N"""

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_FIXTURES = ROOT / "data" / "fixtures"
DATA_ODDS = ROOT / "data" / "odds"
DATA_RESULTS = ROOT / "data" / "results"
CONFIG_PATH = ROOT / "config" / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def add_common_args(p):
    """Add --season, --round, --db to a subparser."""
    p.add_argument("--season", type=int, default=2025)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--db", default=None, help="Path to SQLite database")


def resolve_csv(directory: Path, season: int, round_num: int, prefix: str) -> Path:
    """Try exact naming patterns to find a CSV."""
    patterns = [
        f"{prefix}_round{round_num}_{season}.csv",
        f"sample_round{round_num}_{season}.csv",
    ]
    for p in patterns:
        candidate = directory / p
        if candidate.exists():
            return candidate
    csvs = sorted(directory.glob("*.csv"))
    if csvs:
        return csvs[0]
    raise FileNotFoundError(f"No CSV found in {directory}")


def cmd_init_db(args):
    from .db import init_db
    init_db(args.db)
    print(f"Database initialised at {args.db or 'afl_tipping_factory.db'}")


def cmd_pre_round(args):
    from .pipeline import run_pre_round
    cfg = load_config()
    teams = cfg.get("afl_teams")

    fixture_csv = args.fixture or str(resolve_csv(DATA_FIXTURES, args.season, args.round, "fixtures"))
    odds_csv = args.odds or str(resolve_csv(DATA_ODDS, args.season, args.round, "odds"))

    print(f"Fixture CSV: {fixture_csv}")
    print(f"Odds CSV:    {odds_csv}")
    run_pre_round(fixture_csv, odds_csv, args.season, args.round, teams=teams, db_path=args.db)


def cmd_post_round(args):
    from .pipeline import run_post_round
    results_csv = args.results or str(resolve_csv(DATA_RESULTS, args.season, args.round, "results"))
    print(f"Results CSV: {results_csv}")
    run_post_round(results_csv, args.season, args.round, db_path=args.db)


def cmd_matrix(args):
    from .db import init_db
    from .matrix import print_tipping_matrix
    init_db(args.db)
    print_tipping_matrix(args.season, args.round, args.db)


def main(argv=None):
    parser = argparse.ArgumentParser(description="AFL Tipping Factory CLI")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init-db", help="Initialise the database")
    p_init.add_argument("--db", default=None)

    pre = sub.add_parser("pre-round", help="Load fixtures/odds, run models, validate, print matrix")
    add_common_args(pre)
    pre.add_argument("--fixture", help="Path to fixture CSV (auto-detected if omitted)")
    pre.add_argument("--odds", help="Path to odds CSV (auto-detected if omitted)")

    post = sub.add_parser("post-round", help="Load results, score predictions, update Elo")
    add_common_args(post)
    post.add_argument("--results", help="Path to results CSV (auto-detected if omitted)")

    mat = sub.add_parser("matrix", help="Print tipping matrix from existing data")
    add_common_args(mat)

    args = parser.parse_args(argv)

    if args.command == "init-db":
        cmd_init_db(args)
    elif args.command == "pre-round":
        cmd_pre_round(args)
    elif args.command == "post-round":
        cmd_post_round(args)
    elif args.command == "matrix":
        cmd_matrix(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
