"""AC5: candidate draw/balance features are present and leak-free."""

from __future__ import annotations

import pandas as pd
import pytest

from worldcup_predictor.features import (
    BALANCE_FEATURE_COLUMNS,
    EXTENDED_FEATURE_COLUMNS,
    FEATURE_COLUMNS,
    build_features_for_results,
)


def _results(n: int = 80) -> pd.DataFrame:
    teams = ["A", "B", "C", "D"]
    rows = []
    for i in range(n):
        home = teams[i % len(teams)]
        away = teams[(i + 1) % len(teams)]
        outcome = i % 3  # ensure draws exist
        hs, as_ = {0: (2, 0), 1: (1, 1), 2: (0, 2)}[outcome]
        rows.append(
            {
                "date": pd.Timestamp("2014-01-01") + pd.Timedelta(days=i),
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
                "tournament": "Friendly",
                "neutral": 0,
            }
        )
    return pd.DataFrame(rows)


def test_balance_columns_present_and_not_wired_to_production():
    feats = build_features_for_results(_results(60))
    for column in BALANCE_FEATURE_COLUMNS:
        assert column in feats.columns
        assert feats[column].notna().all()
    # Candidate features stay OUT of production until an ablation proves a gain.
    assert all(c not in FEATURE_COLUMNS for c in BALANCE_FEATURE_COLUMNS)
    assert EXTENDED_FEATURE_COLUMNS == FEATURE_COLUMNS + BALANCE_FEATURE_COLUMNS


def test_abs_features_equal_absolute_of_diffs():
    feats = build_features_for_results(_results(60))
    assert (feats["abs_elo_diff"] == feats["elo_diff"].abs()).all()
    assert (feats["abs_recent_form_5_diff"] == feats["recent_form_5_diff"].abs()).all()
    assert (feats["abs_recent_form_10_diff"] == feats["recent_form_10_diff"].abs()).all()


def test_draw_rate_is_leak_free():
    # The first match of every team has no prior history, so the draw rate must
    # fall back to the default prior, never reflect the current/own match.
    results = _results(60).sort_values("date").reset_index(drop=True)
    feats = build_features_for_results(results)
    # draw_rate_combined is bounded in [0, 1].
    assert feats["draw_rate_combined"].between(0.0, 1.0).all()
    # A team's very first appearance uses the default prior (0.25), proving the
    # rolling stat excludes the current match.
    first_match = feats.iloc[0]
    assert first_match["draw_rate_combined"] == pytest.approx(0.25, abs=1e-9)
