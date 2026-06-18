"""Walk-forward validation runner (Phase 3 AC1/AC2/AC7).

Runs multi-window temporal validation, writes an aggregate + segmented report,
and re-measures the production feature set under the same protocol so the
Phase 2 baseline can be compared like-for-like.

Examples:
    python scripts/walk_forward_validation.py --results data/raw/international_results.csv
    python scripts/walk_forward_validation.py --feature-set extended --n-windows 6 --test-size 250
"""

from __future__ import annotations

import argparse
from pathlib import Path

from worldcup_predictor.config import DEFAULT_RESULTS_PATH, OUTPUT_DIR
from worldcup_predictor.data import load_results
from worldcup_predictor.features import EXTENDED_FEATURE_COLUMNS, FEATURE_COLUMNS
from worldcup_predictor.reliability import dataset_reliability, warning_banner
from worldcup_predictor.walk_forward import aggregate_dataframe, report_markdown, walk_forward_backtest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Walk-forward validation for the 1X2 predictor.")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS_PATH)
    parser.add_argument("--n-windows", type=int, default=5)
    parser.add_argument("--test-size", type=int, default=200)
    parser.add_argument("--min-train", type=int, default=200)
    parser.add_argument(
        "--feature-set",
        choices=["base", "extended"],
        default="base",
        help="base = production FEATURE_COLUMNS; extended = + candidate draw/balance features (ablation).",
    )
    parser.add_argument("--output-md", type=Path, default=OUTPUT_DIR / "walk_forward_report.md")
    parser.add_argument("--output-csv", type=Path, default=OUTPUT_DIR / "walk_forward_report.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = load_results(args.results)

    reliability = dataset_reliability(results)
    if not reliability.ok:
        print(warning_banner(reliability))

    feature_columns = EXTENDED_FEATURE_COLUMNS if args.feature_set == "extended" else FEATURE_COLUMNS
    report = walk_forward_backtest(
        results,
        n_windows=args.n_windows,
        test_size=args.test_size,
        feature_columns=feature_columns,
        min_train=args.min_train,
    )

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(report_markdown(report), encoding="utf-8")
    aggregate_dataframe(report).to_csv(args.output_csv, index=False)

    print(report_markdown(report))
    print(f"Wrote walk-forward report to {args.output_md} and {args.output_csv}")


if __name__ == "__main__":
    main()
