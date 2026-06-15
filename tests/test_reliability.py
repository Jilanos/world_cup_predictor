from __future__ import annotations

import pandas as pd

from worldcup_predictor.reliability import dataset_reliability, warning_banner


def _results(n: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2000-01-01", periods=n, freq="D"),
            "home_team": ["A"] * n,
            "away_team": ["B"] * n,
            "home_score": [1] * n,
            "away_score": [0] * n,
        }
    )


def test_below_threshold_is_unreliable():
    status = dataset_reliability(_results(12), threshold=2000)
    assert status.ok is False
    assert status.n_matches == 12
    assert "UNRELIABLE" in status.message


def test_at_or_above_threshold_is_ok():
    status = dataset_reliability(_results(2000), threshold=2000)
    assert status.ok is True
    assert status.n_matches == 2000
    assert "OK" in status.message


def test_custom_threshold_is_respected():
    assert dataset_reliability(_results(50), threshold=10).ok is True
    assert dataset_reliability(_results(5), threshold=10).ok is False


def test_warning_banner_contains_message():
    status = dataset_reliability(_results(1), threshold=2000)
    banner = warning_banner(status)
    assert status.message in banner
    assert "!" in banner
