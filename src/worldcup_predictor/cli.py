from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .config import (
    DEFAULT_ELO_PATH,
    DEFAULT_FIFA_PATH,
    DEFAULT_FIXTURES_PATH,
    DEFAULT_ODDS_PATH,
    DEFAULT_PREDICTIONS_CSV,
    DEFAULT_PREDICTIONS_MD,
    DEFAULT_RESULTS_PATH,
)
from .data import load_elo, load_fifa, load_fixtures, load_odds, load_results
from .elo import rolling_elo
from .features import build_features_for_results, build_fixture_features
from .model import (
    LABELS,
    blend_with_market,
    confidence_level,
    predict_probabilities,
    time_decay_weights,
    train_result_model,
)
from .output import OUTPUT_COLUMNS, write_outputs
from .reliability import dataset_reliability, warning_banner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict World Cup fixture outcomes.")
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES_PATH)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS_PATH)
    parser.add_argument("--elo", type=Path, default=DEFAULT_ELO_PATH)
    parser.add_argument("--fifa", type=Path, default=DEFAULT_FIFA_PATH)
    parser.add_argument("--odds", type=Path, default=DEFAULT_ODDS_PATH)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_PREDICTIONS_CSV)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_PREDICTIONS_MD)
    parser.add_argument("--market-weight", type=float, default=0.35)
    return parser.parse_args()


def _prediction_name(result: str, home_team: str, away_team: str) -> str:
    if result == "home":
        return home_team
    if result == "away":
        return away_team
    return "Draw"


def _explanation(row: pd.Series, result: str, used_market: bool) -> str:
    reasons = []
    if abs(row["elo_diff"]) >= 75:
        stronger = row["home_team"] if row["elo_diff"] > 0 else row["away_team"]
        reasons.append(f"{stronger} has the stronger Elo profile")
    if abs(row["recent_form_5_diff"]) >= 0.15:
        stronger = row["home_team"] if row["recent_form_5_diff"] > 0 else row["away_team"]
        reasons.append(f"{stronger} has better recent form")
    if abs(row["goals_for_pg_diff"]) >= 0.25:
        stronger = row["home_team"] if row["goals_for_pg_diff"] > 0 else row["away_team"]
        reasons.append(f"{stronger} has produced more goals recently")
    if used_market:
        reasons.append("bookmaker odds were included")
    if not reasons:
        reasons.append("teams project closely on recent performance")
    return f"Pick: {result}. " + "; ".join(reasons[:3]) + "."


def run(args: argparse.Namespace) -> pd.DataFrame:
    fixtures = load_fixtures(args.fixtures)
    results = load_results(args.results)

    reliability = dataset_reliability(results)
    if not reliability.ok:
        print(warning_banner(reliability))

    elo = load_elo(args.elo)
    fifa = load_fifa(args.fifa)
    odds = load_odds(args.odds)

    elo_ratings = rolling_elo(results)
    train_features = build_features_for_results(results, elo_ratings.pre_match, include_target=True)
    weights = time_decay_weights(train_features["date"])
    model = train_result_model(train_features, sample_weight=weights)

    fixture_features = build_fixture_features(
        fixtures,
        results,
        elo_final=elo_ratings.final,
        manual_elo=elo,
        fifa=fifa,
        odds=odds,
    )
    model_probs = predict_probabilities(model, fixture_features)
    probabilities = blend_with_market(model_probs, fixture_features, market_weight=args.market_weight)

    rows = []
    for idx, feature_row in fixture_features.iterrows():
        probs = probabilities.loc[idx, LABELS]
        predicted_result = str(probs.idxmax())
        used_market = bool(
            np.isfinite(feature_row[["market_home", "market_draw", "market_away"]].astype(float)).all()
        )
        rows.append(
            {
                "date": pd.Timestamp(feature_row["date"]).date().isoformat(),
                "home_team": feature_row["home_team"],
                "away_team": feature_row["away_team"],
                "predicted_result": predicted_result,
                "predicted_winner_or_draw": _prediction_name(
                    predicted_result,
                    str(feature_row["home_team"]),
                    str(feature_row["away_team"]),
                ),
                "probability_home_win": round(float(probs["home"]), 4),
                "probability_draw": round(float(probs["draw"]), 4),
                "probability_away_win": round(float(probs["away"]), 4),
                "confidence_level": confidence_level(float(probs.max())),
                "short_explanation": _explanation(feature_row, predicted_result, used_market),
            }
        )

    predictions = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    write_outputs(predictions, args.output_csv, args.output_md)
    return predictions


def main() -> None:
    args = parse_args()
    predictions = run(args)
    print(f"Wrote {len(predictions)} predictions to {args.output_csv} and {args.output_md}")


if __name__ == "__main__":
    main()
