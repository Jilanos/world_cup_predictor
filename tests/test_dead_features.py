"""AC3: FIFA/market columns are not dead, misleading model inputs anymore.

They were constant at training time, so the gradient-boosted model never split
on them and its output was provably invariant to them while real values were
injected at fixture time. Phase 3 removes them from the production feature set;
market signal is applied only as post-processing (`blend_with_market`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from worldcup_predictor.features import FEATURE_COLUMNS, build_features_for_results
from worldcup_predictor.model import LABELS, predict_probabilities, train_result_model


def _results(n: int = 120) -> pd.DataFrame:
    teams = ["A", "B", "C", "D", "E", "F"]
    rows = []
    for i in range(n):
        home = teams[i % len(teams)]
        away = teams[(i + 2) % len(teams)]
        outcome = i % 3
        hs, as_ = {0: (2, 0), 1: (1, 1), 2: (0, 2)}[outcome]
        rows.append(
            {
                "date": pd.Timestamp("2012-01-01") + pd.Timedelta(days=i),
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
                "tournament": "Friendly",
                "neutral": 0,
            }
        )
    return pd.DataFrame(rows)


def test_feature_columns_exclude_dead_fifa_and_market():
    for dead in ["fifa_rank_diff", "fifa_points_diff", "market_home", "market_draw", "market_away"]:
        assert dead not in FEATURE_COLUMNS


def test_model_prediction_invariant_to_fifa_and_market_columns():
    feats = build_features_for_results(_results(120), include_target=True)
    model = train_result_model(feats, calibrate=False)

    baseline = predict_probabilities(model, feats)[LABELS].to_numpy()

    mutated = feats.copy()
    rng = np.random.default_rng(0)
    mutated["fifa_rank_diff"] = rng.normal(size=len(mutated)) * 50
    mutated["fifa_points_diff"] = rng.normal(size=len(mutated)) * 500
    mutated["market_home"] = rng.random(size=len(mutated))
    mutated["market_draw"] = rng.random(size=len(mutated))
    mutated["market_away"] = rng.random(size=len(mutated))
    after = predict_probabilities(model, mutated)[LABELS].to_numpy()

    # The production model never sees these columns, so its output is identical.
    np.testing.assert_allclose(baseline, after, rtol=0, atol=0)
