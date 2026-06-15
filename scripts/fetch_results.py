#!/usr/bin/env python3
"""Download the public martj42 international-results dataset into data/raw/.

Usage:
    python scripts/fetch_results.py            # skip if file already exists
    python scripts/fetch_results.py --force    # re-download and overwrite
    python scripts/fetch_results.py --out path/to/results.csv

If you cannot or do not want to download automatically, follow the manual
steps in the README ("Required: historical international results").
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from worldcup_predictor.config import DEFAULT_RESULTS_PATH
from worldcup_predictor.data_sources import MARTJ42_RESULTS_URL, fetch_results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_RESULTS_PATH)
    parser.add_argument("--url", default=MARTJ42_RESULTS_URL)
    parser.add_argument("--force", action="store_true", help="Overwrite an existing file.")
    args = parser.parse_args()

    if args.out.exists() and not args.force:
        print(f"{args.out} already exists; use --force to re-download.")
        return 0

    try:
        path = fetch_results(args.out, url=args.url, overwrite=True)
    except Exception as error:  # noqa: BLE001 - surface a friendly message
        print(f"Download failed: {error}", file=sys.stderr)
        print(
            "Fallback: download results.csv manually from the public "
            "'martj42/international_results' GitHub repo and copy it to "
            f"{args.out}.",
            file=sys.stderr,
        )
        return 1

    line_count = sum(1 for _ in path.open(encoding="utf-8")) - 1
    print(f"Wrote {line_count} matches to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
