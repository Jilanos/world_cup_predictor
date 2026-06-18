"""AC1/AC2: walk-forward multi-window validation and leak-free segments."""

from __future__ import annotations

import pandas as pd

from worldcup_predictor.features import EXTENDED_FEATURE_COLUMNS
from worldcup_predictor.walk_forward import (
    build_segments,
    report_markdown,
    walk_forward_backtest,
)
from worldcup_predictor.elo import rolling_elo


def _results(n: int = 700) -> pd.DataFrame:
    teams = [f"T{i}" for i in range(12)]
    rows = []
    for i in range(n):
        home = teams[i % len(teams)]
        away = teams[(i + 5) % len(teams)]
        outcome = i % 3
        hs, as_ = {0: (2, 0), 1: (1, 1), 2: (0, 2)}[outcome]
        rows.append(
            {
                "date": pd.Timestamp("2005-01-01") + pd.Timedelta(days=i),
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
                "tournament": "FIFA World Cup qualification" if i % 4 else "Friendly",
                "neutral": i % 5 == 0,
            }
        )
    return pd.DataFrame(rows)


def test_walk_forward_produces_multiple_windows_and_aggregate():
    report = walk_forward_backtest(_results(700), n_windows=3, test_size=100, min_train=100)
    assert report["n_windows"] == 3
    assert len(report["windows"]) == 3
    strategies = {a["strategy"] for a in report["aggregate"]}
    assert {"model", "baseline: base rate", "baseline: uniform", "market-only"} <= strategies
    for a in report["aggregate"]:
        assert "log_loss_mean" in a and "log_loss_std" in a
    assert report["ranking"][0] in strategies


def test_walk_forward_windows_are_leak_free():
    report = walk_forward_backtest(_results(700), n_windows=3, test_size=100, min_train=100)
    for w in report["windows"]:
        assert w["train_end"] <= w["test_start"]
        assert w["train_size"] >= 100


def test_segments_are_leak_free_and_counted():
    results = _results(300).sort_values("date").reset_index(drop=True)
    elo = rolling_elo(results)
    seg = build_segments(results, elo.pre_match)
    assert len(seg) == len(results)
    for column in ["competition_type", "is_neutral", "major_competition", "elo_balance_bucket", "favorite_bucket"]:
        assert column in seg.columns
        assert seg[column].notna().all()


def test_walk_forward_report_has_segments_with_n():
    report = walk_forward_backtest(_results(700), n_windows=2, test_size=100, min_train=100)
    assert report["segments"], "expected segmented metrics"
    for s in report["segments"]:
        assert s["n"] >= 0
        assert "indicative" in s
    md = report_markdown(report)
    assert "Walk-forward validation" in md
    assert "Segments" in md


def test_extended_feature_set_runs():
    report = walk_forward_backtest(
        _results(700), n_windows=2, test_size=100, min_train=100, feature_columns=EXTENDED_FEATURE_COLUMNS
    )
    assert report["n_windows"] == 2
    assert len(report["feature_columns"]) == len(EXTENDED_FEATURE_COLUMNS)
