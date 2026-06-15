from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from worldcup_predictor.backtest import score, temporal_split
from worldcup_predictor.config import (
    DEFAULT_RESULTS_PATH,
    ELO_HOME_ADVANTAGE,
    ELO_K,
    HALF_LIFE_YEARS,
    RANDOM_STATE,
)
from worldcup_predictor.data import load_results
from worldcup_predictor.elo import rolling_elo
from worldcup_predictor.features import FEATURE_COLUMNS, build_features_for_results, result_label
from worldcup_predictor.model import LABELS, predict_probabilities, time_decay_weights


@dataclass(frozen=True)
class ExperimentResult:
    model: str
    elo_k: float
    elo_home_advantage: float
    half_life_years: float | None
    train_size: int
    test_size: int
    log_loss: float
    brier: float
    accuracy: float


def _estimator(name: str) -> object:
    if name == "logistic":
        return LogisticRegression(max_iter=5000, random_state=RANDOM_STATE)
    if name == "hgb":
        return HistGradientBoostingClassifier(
            random_state=RANDOM_STATE, max_iter=300, learning_rate=0.05, max_depth=3
        )
    raise ValueError(f"Unknown model: {name}")


def _fit_model(name: str, train_features: pd.DataFrame, sample_weight) -> object:
    estimator = _estimator(name)
    model = CalibratedClassifierCV(estimator, method="sigmoid", cv=3)
    fit_kwargs = {} if sample_weight is None else {"sample_weight": sample_weight}
    return model.fit(train_features[FEATURE_COLUMNS], train_features["target"], **fit_kwargs)


def run_experiment(
    results: pd.DataFrame,
    *,
    model_name: str,
    elo_k: float,
    elo_home_advantage: float,
    half_life_years: float | None,
    test_fraction: float,
    max_test: int | None,
) -> ExperimentResult:
    ordered = results.sort_values("date", kind="stable").reset_index(drop=True)
    train, test = temporal_split(ordered, test_fraction=test_fraction, max_test=max_test)
    targets = pd.Series(
        [result_label(int(h), int(a)) for h, a in zip(test["home_score"], test["away_score"])]
    ).reset_index(drop=True)

    elo = rolling_elo(ordered, k=elo_k, home_advantage=elo_home_advantage)
    features = build_features_for_results(ordered, elo.pre_match, include_target=True)
    train_features = features.loc[train.index]
    test_features = features.loc[test.index]
    weights = time_decay_weights(train_features["date"], half_life=half_life_years)
    model = _fit_model(model_name, train_features, weights)
    probs = predict_probabilities(model, test_features)[LABELS].to_numpy()
    metrics = score(probs, targets, model_name)
    return ExperimentResult(
        model=model_name,
        elo_k=float(elo_k),
        elo_home_advantage=float(elo_home_advantage),
        half_life_years=None if half_life_years is None else float(half_life_years),
        train_size=len(train),
        test_size=len(test),
        log_loss=metrics.log_loss,
        brier=metrics.brier,
        accuracy=metrics.accuracy,
    )


def _parse_floats(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare 1X2 model and Elo settings by temporal backtest.")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS_PATH)
    parser.add_argument("--models", default="logistic,hgb")
    parser.add_argument("--elo-k", default="20,30,40")
    parser.add_argument("--elo-home-advantage", default="60,80,100")
    parser.add_argument("--half-life-years", type=float, default=HALF_LIFE_YEARS)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--max-test", type=int, default=1000)
    parser.add_argument("--output-csv", type=Path, default=Path("outputs/model_selection.csv"))
    parser.add_argument("--output-md", type=Path, default=Path("outputs/model_selection.md"))
    return parser.parse_args()


def _markdown(df: pd.DataFrame) -> str:
    lines = [
        "# Model selection",
        "",
        "Temporal backtest comparison for the 1X2 predictor. Lower log-loss and Brier are better; higher accuracy is better.",
        "",
        "| model | elo_k | elo_home_advantage | half_life_years | log_loss | brier | accuracy |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"| {row['model']} | {row['elo_k']:.0f} | {row['elo_home_advantage']:.0f} | "
            f"{row['half_life_years']:.1f} | {row['log_loss']:.4f} | "
            f"{row['brier']:.4f} | {row['accuracy']:.4f} |"
        )
    best = df.iloc[0]
    lines.extend(
        [
            "",
            "Selected production defaults:",
            f"- model: `{best['model']}`",
            f"- `ELO_K`: `{best['elo_k']:.0f}`",
            f"- `ELO_HOME_ADVANTAGE`: `{best['elo_home_advantage']:.0f}`",
            f"- `HALF_LIFE_YEARS`: `{best['half_life_years']:.1f}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    results = load_results(args.results)
    models = [model.strip() for model in args.models.split(",") if model.strip()]
    rows = []
    for model in models:
        for elo_k in _parse_floats(args.elo_k):
            for home_advantage in _parse_floats(args.elo_home_advantage):
                rows.append(
                    asdict(
                        run_experiment(
                            results,
                            model_name=model,
                            elo_k=elo_k,
                            elo_home_advantage=home_advantage,
                            half_life_years=args.half_life_years,
                            test_fraction=args.test_fraction,
                            max_test=args.max_test,
                        )
                    )
                )

    df = pd.DataFrame(rows).sort_values(["log_loss", "brier", "accuracy"], ascending=[True, True, False])
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output_csv, index=False)
    args.output_md.write_text(_markdown(df), encoding="utf-8")
    print(_markdown(df.head(10)))
    print(f"Wrote model selection results to {args.output_csv} and {args.output_md}")


if __name__ == "__main__":
    main()
