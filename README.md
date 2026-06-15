# World Cup Predictor

A pragmatic Python project for predicting FIFA World Cup match outcomes for a private prediction game.

The pipeline reads local CSV files, trains a calibrated 1X2 classifier on historical international results, optionally blends probabilities with bookmaker implied probabilities, then writes:

- `outputs/predictions.csv`
- `outputs/predictions_pretty.md`

## Setup

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Data Files

Create these folders if they do not already exist:

```bash
mkdir -p data/raw data/manual outputs
```

### Required: fixtures

Place upcoming fixtures at:

```text
data/manual/fixtures.csv
```

Required columns:

```csv
date,home_team,away_team
2026-06-11,Mexico,South Africa
```

Optional columns:

```csv
neutral,tournament_importance
```

For World Cup matches, `neutral` is usually `1`. `tournament_importance` can be left out; the default is `1.0`.

### Required: historical international results

Use the public `martj42/international_results` dataset and place the results CSV at:

```text
data/raw/international_results.csv
```

Expected columns:

```csv
date,home_team,away_team,home_score,away_score,tournament,city,country,neutral
```

How to collect it automatically:

```bash
python scripts/fetch_results.py            # downloads ~48k matches to data/raw/
python scripts/fetch_results.py --force    # re-download / refresh
```

The script downloads `results.csv` from the public `martj42/international_results`
repository, validates the header, and writes it atomically. It will **not**
overwrite an existing file unless you pass `--force`.

Manual fallback:

1. Go to the public GitHub repository `martj42/international_results`.
2. Download the CSV file from the repository using the GitHub UI, `git clone`, or GitHub raw file URL.
3. Rename or copy it to `data/raw/international_results.csv`.

Do not scrape websites that disallow scraping. This project is designed for public datasets, APIs, and manual CSV exports.

> **Reliability guardrail.** The shipped example results file has only ~12
> matches — far too few to train a trustworthy model. If the historical results
> file has fewer than `MIN_RESULTS_FOR_RELIABLE` matches (default 2000, see
> `src/worldcup_predictor/config.py`), `worldcup-predict`, `worldcup-backtest`,
> and the dashboard show a loud **UNRELIABLE** warning. Fetch the full dataset
> before trusting any prediction.

### Optional: Elo rankings

Place at:

```text
data/manual/elo_rankings.csv
```

Expected columns:

```csv
team,elo
France,2035
Brazil,1998
```

Use a manually exported CSV from a source you are allowed to use, or maintain your own ratings. If omitted, the project derives a simple historical Elo-like strength estimate from the results file.

### Optional: FIFA rankings

Place at:

```text
data/manual/fifa_rankings.csv
```

Expected columns:

```csv
team,rank,points
Argentina,1,1885.36
Spain,2,1867.09
```

Use an official FIFA ranking table export if available, an API you are allowed to use, or a manually prepared CSV. `points` is optional in spirit but the column should exist; leave it blank if unknown.

### Optional: bookmaker odds

Place at:

```text
data/manual/bookmaker_odds.csv
```

Expected decimal-odds columns:

```csv
date,home_team,away_team,home_odds,draw_odds,away_odds
2026-06-11,Mexico,South Africa,1.70,3.70,5.40
```

Use manual exports from your bookmaker account or a licensed odds API. The code removes the bookmaker overround and blends market probabilities into the model with a default weight of `0.35`.

## Run

```bash
worldcup-predict
```

Or run with explicit paths:

```bash
worldcup-predict \
  --fixtures data/manual/fixtures.csv \
  --results data/raw/international_results.csv \
  --elo data/manual/elo_rankings.csv \
  --fifa data/manual/fifa_rankings.csv \
  --odds data/manual/bookmaker_odds.csv
```

If you do not have Elo, FIFA, or odds files, omit those files from `data/manual/`; the loader treats them as optional.

## Output Columns

`outputs/predictions.csv` contains:

```text
date
home_team
away_team
predicted_result
predicted_winner_or_draw
probability_home_win
probability_draw
probability_away_win
confidence_level
short_explanation
```

The project predicts the **result only** (home win / draw / away win). It does
not predict exact scores.

## Updating Data

1. Replace `data/raw/international_results.csv` with the latest public dataset export.
2. Update `data/manual/fixtures.csv` with the fixtures you want to predict.
3. Optionally refresh `data/manual/elo_rankings.csv`, `data/manual/fifa_rankings.csv`, and `data/manual/bookmaker_odds.csv`.
4. Run `worldcup-predict`.
5. Open `outputs/predictions.csv` or `outputs/predictions_pretty.md`.

## Backtest (measure reliability)

Before trusting predictions, measure them. The backtest splits the historical
results **chronologically** (train on the past, test on the most recent matches —
no shuffling, no leakage) and scores the model against simple baselines:

```bash
worldcup-backtest
worldcup-backtest --test-fraction 0.2 --max-test 400
```

It writes `outputs/backtest_report.md` and `outputs/backtest_report.csv` with:

- `log_loss` and `brier` (lower is better) — probabilistic quality / calibration
- `accuracy` (higher is better) — argmax pick correctness

compared across three strategies: the selected model, a base-rate baseline
(empirical home/draw/away frequencies), and a uniform baseline. **A model that
does not beat the base-rate baseline is not adding value.**

Measured baseline on the full dataset (train 48,417 matches -> most recent 1,000
as test):

| strategy            | log_loss | brier  | accuracy |
| ------------------- | -------- | ------ | -------- |
| model (HGB)         | 0.845    | 0.496  | 61.5%    |
| baseline: base rate | 1.046    | 0.630  | 48.6%    |
| baseline: uniform   | 1.099    | 0.667  | 48.6%    |

The model now clearly beats both baselines on every metric. The full ~48k-match
backtest runs in a few seconds (feature building is vectorized and Elo is a
single sequential pass).

Phase 2 model selection can be reproduced with:

```bash
python scripts/model_selection.py
```

It writes `outputs/model_selection.csv` and `outputs/model_selection.md`, comparing calibrated logistic regression against calibrated histogram gradient boosting while sweeping Elo K-factor and home advantage. The retained production defaults are documented in `src/worldcup_predictor/config.py` and `src/worldcup_predictor/model.py`.

## Local Dashboard

Start the local site with:

```bash
worldcup-site
```

Then open:

```text
http://127.0.0.1:8765
```

The dashboard shows which CSV files are present, which required columns are missing, a preview of each file, and the latest predictions output. It also provides buttons to:

- refresh file status
- copy the example CSV files into `data/`
- run predictions
- include or exclude Elo, FIFA rankings, and bookmaker odds
- adjust the market blend weight used when odds are available

## Team Name Aliases

If a team appears under different names across files, add the mapping in:

```text
src/worldcup_predictor/team_aliases.py
```

Keep aliases there only. The model code should not hardcode team names.

## Model Notes

This is intentionally a compact baseline:

- A calibrated gradient-boosting model (selected over logistic by backtest) predicts `home`, `draw`, or `away` — the result only, no score.
- Training matches are weighted by recency (time-decay, half-life set in `config.py`).
- Features include a leak-free rolling Elo difference (K and home advantage tuned by backtest), recent form, goals for and against, clean sheets, win rate, neutral venue, tournament importance, optional FIFA differences, and optional market probabilities.
- If odds are available, model probabilities are blended with normalized market probabilities.

This should be good enough for a private game baseline, easy to update, and easy to inspect. It is not intended to be a betting system.
