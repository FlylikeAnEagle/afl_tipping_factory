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
│   ├── fixtures/               # Manual fixture CSVs
│   ├── odds/                   # Manual odds CSVs
│   └── results/                # Manual results CSVs
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
