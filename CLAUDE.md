# AFL Tipping Factory

Local Python + SQLite system for AFL footy tipping predictions.

## Objective
Maximise points in straight head-to-head AFL tipping (1pt correct winner, 0pt incorrect).

## Key Metric
Not just strike rate — whether model fades against the bookie favourite actually win points.

## V1 Scope
- Manual fixture CSV loading
- Manual odds CSV loading
- Implied probability with overround removal
- Bookie favourite detection
- Elo baseline with HGA
- AFL-specific features
- Validation gate
- Tipping matrix
- Prediction recording & scoring
- Fade tracking
- pytest coverage

## NOT in V1
- Live scraping
- OpenClaw / agent automation
- Live odds automation

## Engineering Rules
- Python 3.11+, sqlite3, pandas, pyyaml, pytest
- Parameterized SQL
- `.env`, `*.db`, logs, `.venv` out of git
- Never overwrite manual odds with generated data
- Fade success rate = NULL when no fades (not 0.0)
- Run tests before declaring tasks complete
