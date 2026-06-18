from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier

from .config import HALF_LIFE_YEARS, RANDOM_STATE
from .features import FEATURE_COLUMNS


LABELS = ["home", "draw", "away"]

# Calibration needs at least this many examples of the rarest class per fold.
_MIN_PER_CLASS_FOR_CALIBRATION = 3
_CALIBRATION_FOLDS = 3


def _base_estimator() -> HistGradientBoostingClassifier:
    # Backtest selection (Phase 2): gradient boosting beat calibrated logistic
    # on log-loss. It handles missing market columns natively and needs no
    # scaling. No class_weight — calibration handles probability quality without
    # biasing the (minority) draw prior.
    return HistGradientBoostingClassifier(
        random_state=RANDOM_STATE, max_iter=300, learning_rate=0.05, max_depth=3
    )


def _can_calibrate(y: pd.Series) -> bool:
    counts = y.value_counts()
    return len(counts) >= 2 and int(counts.min()) >= _MIN_PER_CLASS_FOR_CALIBRATION * _CALIBRATION_FOLDS


def time_decay_weights(
    dates: pd.Series, as_of: pd.Timestamp | None = None, half_life: float | None = HALF_LIFE_YEARS
) -> np.ndarray | None:
    """Recency weights: a match `half_life` years before `as_of` gets weight 0.5.

    Returns None when weighting is disabled (half_life falsy), so callers can
    pass the result straight through to fit without special-casing.
    """
    if not half_life:
        return None
    reference = as_of if as_of is not None else dates.max()
    age_years = (reference - dates).dt.days / 365.25
    return np.power(0.5, age_years.to_numpy() / float(half_life))


def train_result_model(
    train_features: pd.DataFrame,
    calibrate: bool = True,
    sample_weight: np.ndarray | None = None,
    feature_columns: list[str] | None = None,
) -> object:
    columns = feature_columns if feature_columns is not None else FEATURE_COLUMNS
    x = train_features[columns]
    y = train_features["target"]
    estimator = _base_estimator()
    fit_kwargs = {} if sample_weight is None else {"sample_weight": sample_weight}
    if calibrate and _can_calibrate(y):
        # Sigmoid (Platt) calibration is stable on modest samples and keeps the
        # multinomial probabilities well-behaved.
        model = CalibratedClassifierCV(estimator, method="sigmoid", cv=_CALIBRATION_FOLDS)
        return model.fit(x, y, **fit_kwargs)
    return estimator.fit(x, y, **fit_kwargs)


def predict_probabilities(
    model: object, features: pd.DataFrame, feature_columns: list[str] | None = None
) -> pd.DataFrame:
    columns = feature_columns if feature_columns is not None else FEATURE_COLUMNS
    probabilities = model.predict_proba(features[columns])
    class_index = {label: i for i, label in enumerate(model.classes_)}
    out = pd.DataFrame(index=features.index)
    for label in LABELS:
        if label in class_index:
            out[label] = probabilities[:, class_index[label]]
        else:
            out[label] = 0.0
    total = out.sum(axis=1)
    return out.div(total.replace(0, np.nan), axis=0).fillna(1 / 3)


def blend_with_market(model_probs: pd.DataFrame, features: pd.DataFrame, market_weight: float = 0.35) -> pd.DataFrame:
    market = features[["market_home", "market_draw", "market_away"]].rename(
        columns={"market_home": "home", "market_draw": "draw", "market_away": "away"}
    )
    has_market = market.notna().all(axis=1)
    blended = model_probs.copy()
    blended.loc[has_market] = (
        (1 - market_weight) * model_probs.loc[has_market] + market_weight * market.loc[has_market]
    )
    return blended.div(blended.sum(axis=1), axis=0)


def confidence_level(max_probability: float) -> str:
    if max_probability >= 0.62:
        return "high"
    if max_probability >= 0.48:
        return "medium"
    return "low"
