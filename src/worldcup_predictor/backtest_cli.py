from __future__ import annotations

import argparse
from pathlib import Path

from .backtest import metrics_dataframe, report_markdown, run_backtest
from .config import DEFAULT_BACKTEST_CSV, DEFAULT_BACKTEST_MD, DEFAULT_RESULTS_PATH
from .data import load_results
from .reliability import dataset_reliability, warning_banner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backtest the World Cup predictor on historical data.")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS_PATH)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--max-test", type=int, default=None, help="Cap the number of test matches.")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_BACKTEST_MD)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_BACKTEST_CSV)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = load_results(args.results)

    reliability = dataset_reliability(results)
    if not reliability.ok:
        print(warning_banner(reliability))

    report = run_backtest(results, test_fraction=args.test_fraction, max_test=args.max_test)

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(report_markdown(report), encoding="utf-8")
    metrics_dataframe(report).to_csv(args.output_csv, index=False)

    print(report_markdown(report))
    print(f"Wrote backtest report to {args.output_md} and {args.output_csv}")


if __name__ == "__main__":
    main()
