# AFL Tipping Factory

Local Python + SQLite system for AFL footy tipping predictions.

## Objective

Maximise points in straight head-to-head AFL tipping competition:
- 1 point for correct outright winner
- 0 points for incorrect

Key metric: not just strike rate, but whether model fades against the bookie favourite actually win points.

## Setup

```bash
pip install -r requirements.txt
```

## Preparing a Real Round

### CSV Templates

Blank templates live in `data/templates/`. Copy them to `data/manual/`, fill in, and run:

```bash
cp data/templates/fixtures_template.csv data/manual/fixtures_round14_2025.csv
cp data/templates/odds_template.csv     data/manual/odds_round14_2025.csv
cp data/templates/results_template.csv   data/manual/results_round14_2025.csv
```

### Quick Start: new-round helper

Create blank CSVs from templates for any round:

```bash
python -m src new-round --season 2026 --round 14
```

This creates:
- `data/manual/fixtures_2026_round14.csv`
- `data/manual/odds_2026_round14.csv`
- `data/manual/results_2026_round14.csv`

Existing files are not overwritten unless you add `--force`.

### Required CSV Columns

| CSV | Required Columns |
|---|---|
| **Fixtures** | `match_id`, `season`, `round`, `home_team`, `away_team` |
| **Odds** | `match_id`, `home_odds`, `away_odds`, `market_source` |
| **Results** | `match_id`, `home_score`, `away_score` |

### Optional Fixture Columns

`match_date` (YYYY-MM-DD), `kickoff_time` (HH:MM), `venue`, `neutral_venue` (0 or 1)

### match_id Format

`{season}R{round}{HomeShort}{AwayShort}` — e.g. `2025R14HawksBlues`

### Valid Team Names

Adelaide, Brisbane, Carlton, Collingwood, Essendon, Fremantle, Geelong, Gold Coast, GWS, Hawthorn, Melbourne, North Melbourne, Port Adelaide, Richmond, St Kilda, Sydney, West Coast, Western Bulldogs

### market_source Prefix

Use `manual_` prefix to protect odds from overwrite: `manual_sportsbet`, `manual_tab`, `manual_pointsbet`

### Real Round Workflow

```bash
# Before the round — fill in fixtures + odds CSVs, then:
python -m src pre-round --round 14 --season 2025 \
  --fixture data/manual/fixtures_round14_2025.csv \
  --odds data/manual/odds_round14_2025.csv

# After the round — fill in results CSV, then:
python -m src post-round --round 14 --season 2025 \
  --results data/manual/results_round14_2025.csv
```

### Input Validation

The loaders validate:
- Missing required columns (friendly error listing found vs required)
- Unrecognised team names (warning with full valid list)
- Odds must be positive decimal numbers
- Match IDs in odds/results must exist in fixtures (load fixtures first)
- Results cannot be loaded before predictions exist (run pre-round first)
- Negative scores rejected

## Manual Round Workflow

### 1. Initialise the database

```bash
python -m src init-db --season 2025 --round 12
```

### 2. Pre-round: load fixtures, odds, run models, validate, print matrix

```bash
python -m src pre-round --season 2025 --round 12
```

This single command:
- Loads fixture CSV from `data/fixtures/`
- Loads odds CSV from `data/odds/`
- Calculates implied probabilities with overround removal
- Detects bookie favourite for each match
- Initialises Elo ratings for all 18 AFL teams
- Runs Elo baseline predictions
- Records bookie favourite predictions
- Builds AFL-specific features (rest days, ladder, form)
- Runs the validation gate
- Prints the tipping matrix

To specify custom CSV paths:

```bash
python -m src pre-round --season 2025 --round 12 \
  --fixture data/fixtures/sample_round12_2025.csv \
  --odds data/odds/sample_round12_2025.csv
```

### 3. After the round: load results and score

```bash
python -m src post-round --season 2025 --round 12
```

This:
- Loads results CSV from `data/results/`
- Validates all results are complete
- Scores all model predictions against actual results
- Tracks fades (model vs bookie favourite)
- Updates Elo ratings
- Prints scoring summary

To specify a custom results CSV:

```bash
python -m src post-round --season 2025 --round 12 \
  --results data/results/sample_round12_2025.csv
```

### 4. Print tipping matrix (standalone)

```bash
python -m src matrix --season 2025 --round 12
```

### Full dry run with sample data

```bash
python -m src pre-round --season 2025 --round 12
python -m src post-round --season 2025 --round 12
```

## Validation Gate

The pre-round pipeline validates:
- Every match has odds (home + away)
- Implied probabilities are calculated
- Bookie favourite is set
- Elo probabilities are generated
- Feature rows exist
- Predictions are recorded

If any check fails, the pipeline exits with errors.

## Fade Tracking

- A "fade" = model picks against the bookie favourite
- `fade_successful` = 1 if fade was correct, 0 if wrong
- If a model had zero fades in a round, `fade_success_rate` is NULL (not 0.0)

## Testing

```bash
python -m pytest -v
```

## Architecture

```
afl_tipping_factory/
├── config/config.yaml          # Teams, Elo settings, venues
├── data/
│   ├── fixtures/               # Sample fixture CSVs
│   ├── odds/                   # Sample odds CSVs
│   ├── results/                # Sample results CSVs
│   ├── templates/              # Blank CSV templates for real rounds
│   └── manual/                 # Your real round data (gitignored)
├── sql/schema.sql              # SQLite schema
├── src/
│   ├── __main__.py             # CLI entrypoint
│   ├── db.py                   # Database connection
│   ├── loaders.py              # CSV loaders
│   ├── probability.py          # Implied probability + overround removal
│   ├── elo.py                  # Elo rating system with HGA
│   ├── features.py             # AFL-specific feature building
│   ├── validation.py           # Validation gate
│   ├── matrix.py               # Tipping matrix output
│   ├── scoring.py              # Prediction scoring + fade tracking
│   └── pipeline.py             # Full pipeline orchestration
└── tests/                      # pytest suite
```

## Model Names

| Model | Description |
|---|---|
| `elo_baseline` | Elo rating system with AFL home ground advantage |
| `bookie_favourite` | Raw bookmaker favourite baseline |
| `claude_manual` | Claude's manual tips (future) |
| `gpt_manual` | GPT's manual tips (future) |
| `anthony_submitted` | Anthony's submitted tips (future) |
