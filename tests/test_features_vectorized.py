from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from worldcup_predictor.features import (
    FEATURE_COLUMNS,
    build_features_for_results,
)


def _synthetic_results(n: int = 80) -> pd.DataFrame:
    teams = ["A", "B", "C", "D", "E"]
    rows = []
    for i in range(n):
        home = teams[i % len(teams)]
        away = teams[(i + 2) % len(teams)]
        hs = (i * 7) % 4
        as_ = (i * 3) % 4
        rows.append(
            {
                "date": pd.Timestamp("2015-01-01") + pd.Timedelta(days=i),
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
                "tournament": "Friendly",
                "neutral": 0,
            }
        )
    return pd.DataFrame(rows)


def _brute_trailing(results: pd.DataFrame, team: str, as_of: pd.Timestamp, window: int, col: str) -> float:
    """Reference (slow) computation mirroring the original per-match logic."""
    mask = results["date"] < as_of
    sub = results[mask]
    rows = []
    for _, r in sub.iterrows():
        if r["home_team"] == team:
            rows.append({"points": _pts(r["home_score"], r["away_score"]), "gf": r["home_score"], "ga": r["away_score"]})
        elif r["away_team"] == team:
            rows.append({"points": _pts(r["away_score"], r["home_score"]), "gf": r["away_score"], "ga": r["home_score"]})
    if not rows:
        return None
    frame = pd.DataFrame(rows).tail(window)
    return float(frame[col].mean())


def _pts(a, b):
    return 3 if a > b else (1 if a == b else 0)


def test_build_features_has_expected_columns_and_no_nans():
    results = _synthetic_results(60)
    feats = build_features_for_results(results)
    for column in FEATURE_COLUMNS:
        assert column in feats.columns
    assert feats[FEATURE_COLUMNS].isna().to_numpy().sum() == 0
    assert "target" in feats.columns
    assert len(feats) == len(results)


def test_vectorized_form_matches_bruteforce():
    results = _synthetic_results(80)
    feats = build_features_for_results(results)

    # Check a handful of late matches where both teams have history.
    for idx in [40, 55, 70, 79]:
        match = results.loc[idx]
        home, away, as_of = match["home_team"], match["away_team"], match["date"]

        bf_home_f10 = _brute_trailing(results, home, as_of, 10, "points")
        bf_away_f10 = _brute_trailing(results, away, as_of, 10, "points")
        expected = (bf_home_f10 / 3) - (bf_away_f10 / 3)
        assert feats.loc[idx, "recent_form_10_diff"] == pytest.approx(expected, abs=1e-9)

        bf_home_gf = _brute_trailing(results, home, as_of, 10, "gf")
        bf_away_gf = _brute_trailing(results, away, as_of, 10, "gf")
        assert feats.loc[idx, "goals_for_pg_diff"] == pytest.approx(bf_home_gf - bf_away_gf, abs=1e-9)


def test_elo_diff_is_not_neutralized_in_training():
    results = _synthetic_results(60)
    feats = build_features_for_results(results)
    # The whole point of Phase 1: elo_diff carries real signal at training time.
    assert feats["elo_diff"].abs().sum() > 0
    # FIFA stays neutral (no historical snapshots) and market stays at the prior.
    assert (feats["fifa_rank_diff"] == 0).all()
    assert feats["market_home"].eq(1 / 3).all()
