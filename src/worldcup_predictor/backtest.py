"""Temporal backtest for the World Cup predictor.

Establishes a *measured* baseline of predictive quality, instead of trusting the
model blindly. It splits the historical results chronologically (train on the
past, test on the most recent matches — no shuffling, no leakage), then scores
the model against simple baselines using log-loss, Brier score, and accuracy.

The model path mirrors the deployed CLI exactly: train with backfilled (neutral)
rating columns, predict on the test set with derived ratings. So the numbers
reflect what the live system actually does.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .elo import rolling_elo
from .features import build_features_for_results, result_label
from .model import LABELS, predict_probabilities, time_decay_weights, train_result_model

EPS = 1e-15


@dataclass(frozen=True)
class Metrics:
    strategy: str
    n: int
    log_loss: float
    brier: float
    accuracy: float


def temporal_split(
    results: pd.DataFrame, test_fraction: float = 0.2, max_test: int | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chronological split: oldest matches train, most recent matches test.

    Uses a stable sort so that, when the input is already chronologically
    ordered, the returned index labels match position exactly. This is critical
    when the caller builds features on a separately-sorted frame and aligns by
    index: an unstable re-sort would reorder same-date ties and silently
    misalign features with outcomes.
    """
    ordered = results.sort_values("date", kind="stable").reset_index(drop=True)
    n = len(ordered)
    n_test = max(1, int(round(n * test_fraction)))
    if max_test is not None:
        n_test = min(n_test, max_test)
    n_test = min(n_test, max(n - 1, 1))
    split = n - n_test
    return ordered.iloc[:split].copy(), ordered.iloc[split:].copy()


def _one_hot(targets: pd.Series) -> np.ndarray:
    index = {label: i for i, label in enumerate(LABELS)}
    matrix = np.zeros((len(targets), len(LABELS)))
    for row, label in enumerate(targets):
        matrix[row, index[label]] = 1.0
    return matrix


def score(probabilities: np.ndarray, targets: pd.Series, strategy: str) -> Metrics:
    """Compute log-loss, Brier, and accuracy for a probability matrix."""
    truth = _one_hot(targets)
    probs = np.asarray(probabilities, dtype=float)
    probs = probs / probs.sum(axis=1, keepdims=True)
    probs = np.clip(probs, EPS, 1.0)

    log_loss = float(-np.mean(np.sum(truth * np.log(probs), axis=1)))
    brier = float(np.mean(np.sum((probs - truth) ** 2, axis=1)))
    predicted = probs.argmax(axis=1)
    actual = truth.argmax(axis=1)
    accuracy = float(np.mean(predicted == actual))
    return Metrics(strategy, len(targets), log_loss, brier, accuracy)


def _base_rate(train: pd.DataFrame) -> np.ndarray:
    labels = [result_label(int(h), int(a)) for h, a in zip(train["home_score"], train["away_score"])]
    counts = pd.Series(labels).value_counts(normalize=True)
    return np.array([counts.get(label, 0.0) for label in LABELS])


def run_backtest(
    results: pd.DataFrame, test_fraction: float = 0.2, max_test: int | None = None
) -> dict[str, object]:
    """Train on the past, evaluate on recent matches, compare to baselines."""
    ordered = results.sort_values("date", kind="stable").reset_index(drop=True)
    train, test = temporal_split(ordered, test_fraction=test_fraction, max_test=max_test)
    targets = pd.Series(
        [result_label(int(h), int(a)) for h, a in zip(test["home_score"], test["away_score"])]
    ).reset_index(drop=True)

    # --- Model (mirrors the deployed CLI path) ---
    # Elo and trailing features computed once over the FULL ordered history so
    # that test-match features include the training history (leak-free: each
    # match only sees matches strictly before it).
    elo_ratings = rolling_elo(ordered)
    all_features = build_features_for_results(ordered, elo_ratings.pre_match, include_target=True)

    train_features = all_features.loc[train.index]
    test_features = all_features.loc[test.index]
    weights = time_decay_weights(train_features["date"])
    model = train_result_model(train_features, sample_weight=weights)
    model_probs = predict_probabilities(model, test_features)[LABELS].to_numpy()

    # --- Baselines ---
    n_test = len(test)
    uniform = np.full((n_test, len(LABELS)), 1 / len(LABELS))
    base = _base_rate(train)
    base_rate = np.tile(base, (n_test, 1))

    metrics = [
        score(model_probs, targets, "model"),
        score(base_rate, targets, "baseline: base rate"),
        score(uniform, targets, "baseline: uniform"),
    ]

    return {
        "train_size": int(len(train)),
        "test_size": int(n_test),
        "train_end": str(train["date"].max().date()) if len(train) else None,
        "test_start": str(test["date"].min().date()) if n_test else None,
        "base_rate": {label: round(float(p), 4) for label, p in zip(LABELS, base)},
        "metrics": [asdict(m) for m in metrics],
        "reliable_sample": n_test >= 200,
    }


def metrics_dataframe(report: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(report["metrics"])[["strategy", "n", "log_loss", "brier", "accuracy"]]


def report_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Backtest report",
        "",
        f"- Train matches: {report['train_size']} (up to {report['train_end']})",
        f"- Test matches: {report['test_size']} (from {report['test_start']})",
        f"- Train base rate: {report['base_rate']}",
        "",
    ]
    if not report["reliable_sample"]:
        lines.append(
            "> WARNING: test sample < 200 matches. These numbers are indicative "
            "only — fetch the full dataset for a meaningful baseline.\n"
        )
    lines.append("| strategy | n | log_loss | brier | accuracy |")
    lines.append("| --- | --- | --- | --- | --- |")
    for m in report["metrics"]:
        lines.append(
            f"| {m['strategy']} | {m['n']} | {m['log_loss']:.4f} | "
            f"{m['brier']:.4f} | {m['accuracy']:.4f} |"
        )
    lines.append("")
    lines.append(
        "Lower log-loss and Brier are better; higher accuracy is better. "
        "A model that does not beat the base-rate baseline is not adding value."
    )
    return "\n".join(lines) + "\n"
