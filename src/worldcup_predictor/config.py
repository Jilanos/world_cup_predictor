from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
MANUAL_DIR = DATA_DIR / "manual"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

DEFAULT_FIXTURES_PATH = MANUAL_DIR / "fixtures.csv"
DEFAULT_RESULTS_PATH = RAW_DIR / "international_results.csv"
DEFAULT_ELO_PATH = MANUAL_DIR / "elo_rankings.csv"
DEFAULT_FIFA_PATH = MANUAL_DIR / "fifa_rankings.csv"
DEFAULT_ODDS_PATH = MANUAL_DIR / "bookmaker_odds.csv"
DEFAULT_PREDICTIONS_CSV = OUTPUT_DIR / "predictions.csv"
DEFAULT_PREDICTIONS_MD = OUTPUT_DIR / "predictions_pretty.md"
DEFAULT_BACKTEST_MD = OUTPUT_DIR / "backtest_report.md"
DEFAULT_BACKTEST_CSV = OUTPUT_DIR / "backtest_report.csv"

RANDOM_STATE = 42

# Time-decay: training matches are weighted by recency with this half-life (in
# years). A match `half_life` years before the most recent training match gets
# half the weight. Chosen by backtest; set to None to disable weighting.
HALF_LIFE_YEARS = 12.0

# Rolling-Elo hyperparameters (tuned by backtest over two test windows).
ELO_K = 30.0
ELO_HOME_ADVANTAGE = 80.0

# Minimum number of historical matches before predictions are considered
# reliable. Below this, the model is overfit on a tiny sample and the pipeline
# emits a loud warning instead of presenting predictions as trustworthy.
# The full martj42 dataset has ~48k matches; this threshold flags the example
# (toy) dataset and any half-empty export.
MIN_RESULTS_FOR_RELIABLE = 2000
