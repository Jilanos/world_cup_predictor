"""Dataset reliability guardrail.

The predictor is only as trustworthy as the history it learns from. With a tiny
results file the classifier overfits and the probabilities are noise. This
module reports whether the dataset is large enough so the CLI and dashboard can
warn the operator instead of presenting toy-data predictions as credible.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import MIN_RESULTS_FOR_RELIABLE


@dataclass(frozen=True)
class ReliabilityStatus:
    ok: bool
    n_matches: int
    threshold: int
    message: str


def dataset_reliability(
    results: pd.DataFrame, threshold: int = MIN_RESULTS_FOR_RELIABLE
) -> ReliabilityStatus:
    """Assess whether ``results`` is large enough for reliable predictions."""
    n = int(len(results))
    if n >= threshold:
        message = (
            f"Dataset OK: {n} historical matches "
            f"(>= {threshold} required for reliable predictions)."
        )
        return ReliabilityStatus(True, n, threshold, message)

    message = (
        f"UNRELIABLE: only {n} historical matches (< {threshold} required). "
        "Predictions are based on too little data and should not be trusted. "
        "Run `python scripts/fetch_results.py` to download the full dataset."
    )
    return ReliabilityStatus(False, n, threshold, message)


def warning_banner(status: ReliabilityStatus) -> str:
    """A loud, multi-line banner for CLI output when the dataset is too small."""
    line = "!" * 72
    return f"\n{line}\n  {status.message}\n{line}\n"
