from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from worldcup_predictor.model import time_decay_weights


def _dates(*offsets_years, end="2025-01-01"):
    end_ts = pd.Timestamp(end)
    return pd.Series([end_ts - pd.Timedelta(days=round(o * 365.25)) for o in offsets_years])


def test_disabled_returns_none():
    assert time_decay_weights(_dates(0, 1, 2), half_life=None) is None
    assert time_decay_weights(_dates(0, 1, 2), half_life=0) is None


def test_most_recent_weight_is_one():
    dates = _dates(0, 5, 10)
    w = time_decay_weights(dates, half_life=5)
    assert w[0] == pytest.approx(1.0, abs=1e-6)


def test_half_life_halves_weight():
    dates = _dates(0, 5, 10)
    w = time_decay_weights(dates, half_life=5)
    # 5 years back -> 0.5, 10 years back -> 0.25
    assert w[1] == pytest.approx(0.5, abs=1e-3)
    assert w[2] == pytest.approx(0.25, abs=1e-3)


def test_weights_are_monotonic_decreasing_with_age():
    dates = _dates(0, 1, 3, 7, 15)
    w = time_decay_weights(dates, half_life=8)
    assert np.all(np.diff(w) < 0)


def test_explicit_as_of_reference():
    dates = _dates(2, 4, 6, end="2025-01-01")
    # Reference at the most recent date -> oldest gets smallest weight.
    w = time_decay_weights(dates, as_of=pd.Timestamp("2025-01-01"), half_life=4)
    assert w[0] > w[1] > w[2]
