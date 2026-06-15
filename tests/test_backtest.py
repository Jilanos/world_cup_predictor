from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from worldcup_predictor.backtest import (
    metrics_dataframe,
    report_markdown,
    run_backtest,
    score,
    temporal_split,
)
from worldcup_predictor.model import LABELS


def _synthetic_results(n: int = 60) -> pd.DataFrame:
    # Deterministic alternating outcomes so the split has all three classes.
    teams = ["A", "B", "C", "D"]
    rows = []
    for i in range(n):
        home = teams[i % len(teams)]
        away = teams[(i + 1) % len(teams)]
        outcome = i % 3  # 0 home, 1 draw, 2 away
        hs, as_ = {0: (2, 0), 1: (1, 1), 2: (0, 2)}[outcome]
        rows.append(
            {
                "date": pd.Timestamp("2010-01-01") + pd.Timedelta(days=i),
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
                "tournament": "Friendly",
                "neutral": 0,
            }
        )
    return pd.DataFrame(rows)


def test_temporal_split_is_chronological_and_sized():
    results = _synthetic_results(50)
    train, test = temporal_split(results, test_fraction=0.2)
    assert len(test) == 10
    assert len(train) == 40
    # No leakage: every test date is on/after the last train date boundary.
    assert train["date"].max() <= test["date"].min()


def test_temporal_split_respects_max_test():
    results = _synthetic_results(50)
    _, test = temporal_split(results, test_fraction=0.5, max_test=5)
    assert len(test) == 5


def test_score_perfect_prediction():
    targets = pd.Series(["home", "draw", "away"])
    perfect = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    metrics = score(perfect, targets, "perfect")
    assert metrics.accuracy == pytest.approx(1.0)
    assert metrics.brier == pytest.approx(0.0, abs=1e-9)
    assert metrics.log_loss == pytest.approx(0.0, abs=1e-9)


def test_score_uniform_logloss_is_ln3():
    targets = pd.Series(["home", "draw", "away"])
    uniform = np.full((3, 3), 1 / 3)
    metrics = score(uniform, targets, "uniform")
    assert metrics.log_loss == pytest.approx(math.log(3), abs=1e-9)
    # Brier for uniform vs one-hot = 3 * ((1/3)^2 ... ) -> 2/3
    assert metrics.brier == pytest.approx(2 / 3, abs=1e-9)


def test_score_normalizes_unnormalized_rows():
    targets = pd.Series(["home"])
    unnormalized = np.array([[2.0, 1.0, 1.0]])  # sums to 4 -> [0.5, 0.25, 0.25]
    metrics = score(unnormalized, targets, "raw")
    assert metrics.accuracy == pytest.approx(1.0)
    assert metrics.log_loss == pytest.approx(-math.log(0.5), abs=1e-9)


def test_run_backtest_structure_and_baselines():
    results = _synthetic_results(60)
    report = run_backtest(results, test_fraction=0.25)
    assert report["train_size"] + report["test_size"] == 60
    strategies = {m["strategy"] for m in report["metrics"]}
    assert "model" in strategies
    assert "baseline: base rate" in strategies
    assert "baseline: uniform" in strategies
    # base_rate probabilities sum to ~1 across the three labels.
    assert sum(report["base_rate"][label] for label in LABELS) == pytest.approx(1.0, abs=1e-3)


def test_temporal_split_stable_order_with_tied_dates():
    # Many matches share dates; an unstable re-sort would reorder ties and
    # break index/position alignment used by run_backtest.
    rows = []
    dates = ["2020-01-01", "2020-01-01", "2020-01-02", "2020-01-02", "2020-01-03"]
    for i in range(30):
        rows.append(
            {
                "date": pd.Timestamp(dates[i % len(dates)]),
                "home_team": f"H{i}",
                "away_team": f"A{i}",
                "home_score": 1,
                "away_score": 0,
                "tournament": "Friendly",
                "neutral": 0,
            }
        )
    results = pd.DataFrame(rows)
    train, test = temporal_split(results, test_fraction=0.3)
    combined = pd.concat([train, test]).reset_index(drop=True)
    expected = results.sort_values("date", kind="stable").reset_index(drop=True)
    pd.testing.assert_frame_equal(combined, expected)


def test_backtest_alignment_recovers_strong_signal_with_tied_dates():
    """End-to-end guard for the stable-sort alignment fix.

    Outcome is fully determined by which side the strong pool is on, and every
    match shares one of a few dates. With correct feature/outcome alignment the
    backtested model learns it (high accuracy); a misalignment collapses it to
    chance.
    """
    giants = [f"G{i}" for i in range(8)]
    minnows = [f"M{i}" for i in range(8)]
    rows = []
    dates = ["2018-06-01", "2018-06-01", "2018-06-01", "2018-06-08", "2018-06-08"]
    for i in range(240):
        g = giants[i % len(giants)]
        m = minnows[(i * 3) % len(minnows)]
        if i % 2 == 0:  # giant at home -> home win
            home, away, hs, as_ = g, m, 2, 0
        else:  # giant away -> away win
            home, away, hs, as_ = m, g, 0, 2
        rows.append(
            {
                "date": pd.Timestamp(dates[i % len(dates)]) + pd.Timedelta(days=7 * (i // len(dates))),
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
                "tournament": "Friendly",
                "neutral": 0,
            }
        )
    results = pd.DataFrame(rows)
    report = run_backtest(results, test_fraction=0.2)
    model_metric = next(m for m in report["metrics"] if m["strategy"] == "model")
    assert model_metric["accuracy"] > 0.8


def test_report_markdown_and_dataframe():
    report = run_backtest(_synthetic_results(60), test_fraction=0.25)
    md = report_markdown(report)
    assert "Backtest report" in md
    assert "log_loss" in md
    df = metrics_dataframe(report)
    assert list(df.columns) == ["strategy", "n", "log_loss", "brier", "accuracy"]
    assert len(df) == 3
