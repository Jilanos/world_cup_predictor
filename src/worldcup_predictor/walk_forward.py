"""Walk-forward (multi-window) temporal validation for the 1X2 predictor.

Phase 3 (AC1/AC2/AC7): the Phase 2 selection used a single recent test window,
which over-trusts one slice of history. This runs several chronological test
windows, each trained only on its past (leak-free), and reports per-window
metrics plus aggregate mean/std and a strategy ranking. It also breaks results
down by leak-free segments (competition type, neutral ground, Elo balance,
favorite/outsider) so we can see *where* the model wins or loses.

The same protocol re-measures the Phase 2 config, so "beats the baseline"
compares like-for-like (mean over windows), not a single window against a
single window.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .backtest import score, _base_rate
from .elo import rolling_elo
from .features import (
    FEATURE_COLUMNS,
    build_features_for_results,
    result_label,
    tournament_importance,
)
from .model import LABELS, predict_probabilities, time_decay_weights, train_result_model


@dataclass(frozen=True)
class WindowResult:
    window: int
    train_size: int
    test_size: int
    train_end: str
    test_start: str
    test_end: str
    metrics: list[dict]


def _competition_type(name: object) -> str:
    text = str(name).lower()
    if "world cup" in text:
        return "world_cup"
    if any(t in text for t in ["euro", "copa", "african cup", "asian cup", "gold cup", "continental"]):
        return "continental"
    if "qualif" in text:
        return "qualification"
    if "friendly" in text:
        return "friendly"
    return "other"


def build_segments(results: pd.DataFrame, elo_pre: pd.DataFrame) -> pd.DataFrame:
    """Leak-free segment labels for each match (aligned to ``results`` index).

    Every column is known before kick-off: competition metadata, neutral flag,
    and pre-match Elo. No outcome information is used.
    """
    elo_diff = (elo_pre["home_elo_pre"] - elo_pre["away_elo_pre"]).reindex(results.index)
    abs_diff = elo_diff.abs()
    tournament = results["tournament"] if "tournament" in results else pd.Series("Unknown", index=results.index)
    neutral = results["neutral"] if "neutral" in results else pd.Series(0, index=results.index)

    seg = pd.DataFrame(index=results.index)
    seg["competition_type"] = tournament.map(_competition_type)
    seg["is_neutral"] = np.where(neutral.astype(float) > 0, "neutral", "home_ground")
    seg["major_competition"] = np.where(
        tournament.map(tournament_importance) >= 1.25, "major", "minor"
    )
    seg["elo_balance_bucket"] = pd.cut(
        abs_diff,
        bins=[-0.1, 50, 150, np.inf],
        labels=["balanced", "moderate", "lopsided"],
    ).astype(object)
    seg["favorite_bucket"] = np.select(
        [elo_diff > 50, elo_diff < -50],
        ["home_favorite", "away_favorite"],
        default="toss_up",
    )
    return seg


def _market_only(features: pd.DataFrame) -> np.ndarray:
    """Market-implied probabilities from the feature frame.

    Without a historical odds source these columns are the neutral prior (1/3),
    so market-only collapses to uniform on the backtest. Kept for AC4 so the
    comparison is explicit and the absence of historical odds is visible.
    """
    market = features[["market_home", "market_draw", "market_away"]].to_numpy(dtype=float)
    market = np.where(np.isfinite(market), market, 1 / 3)
    return market / market.sum(axis=1, keepdims=True)


def walk_forward_backtest(
    results: pd.DataFrame,
    *,
    n_windows: int = 5,
    test_size: int = 200,
    feature_columns: list[str] | None = None,
    min_train: int = 200,
) -> dict[str, object]:
    """Run ``n_windows`` chronological test windows, newest first.

    Each window trains on all matches strictly before its test block. Returns
    per-window metrics, aggregate mean/std per strategy, a ranking by mean
    log-loss, and segmented metrics for the model pooled across windows.
    """
    feature_columns = list(feature_columns) if feature_columns is not None else list(FEATURE_COLUMNS)
    ordered = results.sort_values("date", kind="stable").reset_index(drop=True)
    elo = rolling_elo(ordered)
    all_features = build_features_for_results(ordered, elo.pre_match, include_target=True)
    segments = build_segments(ordered, elo.pre_match)
    total = len(ordered)

    windows: list[WindowResult] = []
    pooled_model = []  # (probs_row, target, segment_row) for segmented metrics
    pooled_targets: list[str] = []
    pooled_seg_idx: list[int] = []

    for i in range(n_windows):
        test_end = total - i * test_size
        test_start = test_end - test_size
        if test_start < min_train:
            break
        train_idx = ordered.index[:test_start]
        test_idx = ordered.index[test_start:test_end]
        train = ordered.loc[train_idx]
        test = ordered.loc[test_idx]
        targets = pd.Series(
            [result_label(int(h), int(a)) for h, a in zip(test["home_score"], test["away_score"])]
        ).reset_index(drop=True)

        train_features = all_features.loc[train_idx]
        test_features = all_features.loc[test_idx]
        weights = time_decay_weights(train_features["date"])
        model = train_result_model(train_features, sample_weight=weights, feature_columns=feature_columns)
        model_probs = predict_probabilities(model, test_features, feature_columns=feature_columns)[
            LABELS
        ].to_numpy()

        n_test = len(test)
        uniform = np.full((n_test, len(LABELS)), 1 / len(LABELS))
        base = np.tile(_base_rate(train), (n_test, 1))
        market = _market_only(test_features)

        metrics = [
            score(model_probs, targets, "model"),
            score(base, targets, "baseline: base rate"),
            score(uniform, targets, "baseline: uniform"),
            score(market, targets, "market-only"),
        ]
        windows.append(
            WindowResult(
                window=i,
                train_size=int(len(train)),
                test_size=int(n_test),
                train_end=str(train["date"].max().date()),
                test_start=str(test["date"].min().date()),
                test_end=str(test["date"].max().date()),
                metrics=[m.__dict__ for m in metrics],
            )
        )

        pooled_model.append(model_probs)
        pooled_targets.extend(targets.tolist())
        pooled_seg_idx.extend(test_idx.tolist())

    aggregate = _aggregate(windows)
    segmented = (
        _segmented_metrics(np.vstack(pooled_model), pooled_targets, segments.loc[pooled_seg_idx])
        if pooled_model
        else []
    )
    return {
        "n_windows": len(windows),
        "test_size": test_size,
        "feature_columns": feature_columns,
        "windows": [w.__dict__ for w in windows],
        "aggregate": aggregate,
        "ranking": [a["strategy"] for a in aggregate],
        "segments": segmented,
        "reliable": len(windows) >= 2 and all(w.test_size >= 50 for w in windows),
    }


def _aggregate(windows: list[WindowResult]) -> list[dict]:
    by_strategy: dict[str, dict[str, list[float]]] = {}
    for w in windows:
        for m in w.metrics:
            slot = by_strategy.setdefault(m["strategy"], {"log_loss": [], "brier": [], "accuracy": []})
            slot["log_loss"].append(m["log_loss"])
            slot["brier"].append(m["brier"])
            slot["accuracy"].append(m["accuracy"])
    rows = []
    for strategy, vals in by_strategy.items():
        rows.append(
            {
                "strategy": strategy,
                "n_windows": len(vals["log_loss"]),
                "log_loss_mean": float(np.mean(vals["log_loss"])),
                "log_loss_std": float(np.std(vals["log_loss"])),
                "brier_mean": float(np.mean(vals["brier"])),
                "brier_std": float(np.std(vals["brier"])),
                "accuracy_mean": float(np.mean(vals["accuracy"])),
                "accuracy_std": float(np.std(vals["accuracy"])),
            }
        )
    return sorted(rows, key=lambda r: (r["log_loss_mean"], r["brier_mean"]))


def _segmented_metrics(probs: np.ndarray, targets: list[str], segments: pd.DataFrame) -> list[dict]:
    targets_series = pd.Series(targets).reset_index(drop=True)
    seg = segments.reset_index(drop=True)
    rows = []
    for column in ["competition_type", "is_neutral", "major_competition", "elo_balance_bucket", "favorite_bucket"]:
        for value, idx in seg.groupby(column).groups.items():
            positions = [seg.index.get_loc(i) for i in idx]
            m = score(probs[positions], targets_series.iloc[positions], f"{column}={value}")
            rows.append(
                {
                    "segment": column,
                    "value": str(value),
                    "n": int(m.n),
                    "log_loss": m.log_loss,
                    "brier": m.brier,
                    "accuracy": m.accuracy,
                    "indicative": bool(m.n < 50),
                }
            )
    return rows


def report_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Walk-forward validation",
        "",
        f"- Windows: {report['n_windows']} (test size {report['test_size']} each)",
        f"- Feature columns: {len(report['feature_columns'])}",
        "",
    ]
    if not report["reliable"]:
        lines.append(
            "> WARNING: fewer than 2 windows or small test windows. Numbers are "
            "indicative only — run on the full dataset for a meaningful baseline.\n"
        )
    lines.append("## Aggregate (mean +/- std over windows)")
    lines.append("")
    lines.append("| strategy | log_loss | brier | accuracy |")
    lines.append("| --- | --- | --- | --- |")
    for a in report["aggregate"]:
        lines.append(
            f"| {a['strategy']} | {a['log_loss_mean']:.4f} +/- {a['log_loss_std']:.4f} "
            f"| {a['brier_mean']:.4f} +/- {a['brier_std']:.4f} "
            f"| {a['accuracy_mean']:.4f} +/- {a['accuracy_std']:.4f} |"
        )
    lines.append("")
    lines.append("## Segments (model, pooled over windows)")
    lines.append("")
    lines.append("| segment | value | n | log_loss | brier | accuracy | |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for s in report["segments"]:
        flag = "indicative" if s["indicative"] else ""
        lines.append(
            f"| {s['segment']} | {s['value']} | {s['n']} | {s['log_loss']:.4f} "
            f"| {s['brier']:.4f} | {s['accuracy']:.4f} | {flag} |"
        )
    lines.append("")
    lines.append(
        "Lower log-loss and Brier are better; higher accuracy is better. "
        "`market-only` collapses to uniform unless a historical odds source is wired."
    )
    return "\n".join(lines) + "\n"


def aggregate_dataframe(report: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(report["aggregate"])
