"""Fetch the public historical international-results dataset.

Source: the public ``martj42/international_results`` GitHub repository
(~48k international matches since 1872), published under a permissive licence.

This module only downloads a file the project README already instructs the user
to obtain. It does not scrape any site, and it never overwrites a present file
unless explicitly asked to refresh.
"""

from __future__ import annotations

import shutil
import tempfile
import urllib.request
from pathlib import Path

from .config import DEFAULT_RESULTS_PATH

# Raw CSV on the default branch of the public dataset repository.
MARTJ42_RESULTS_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)

# Expected header so we fail loudly if the remote layout changes.
EXPECTED_COLUMNS = {"date", "home_team", "away_team", "home_score", "away_score", "tournament"}


def _validate_header(first_line: str) -> None:
    header = {column.strip() for column in first_line.split(",")}
    missing = EXPECTED_COLUMNS - header
    if missing:
        raise ValueError(
            "Downloaded file does not look like the expected results dataset; "
            f"missing columns: {sorted(missing)}"
        )


def fetch_results(
    destination: Path = DEFAULT_RESULTS_PATH,
    *,
    url: str = MARTJ42_RESULTS_URL,
    overwrite: bool = False,
    timeout: float = 30.0,
) -> Path:
    """Download the results dataset to ``destination``.

    Returns the destination path. Writes atomically and validates the header
    before replacing any existing file. If ``overwrite`` is False and the file
    already exists, the download is skipped.
    """
    destination = Path(destination)
    if destination.exists() and not overwrite:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "worldcup-predictor"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (trusted URL)
        payload = response.read().decode("utf-8")

    first_line = payload.split("\n", 1)[0]
    _validate_header(first_line)

    # Atomic replace via a temp file in the same directory.
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=destination.parent, delete=False, suffix=".tmp"
    ) as handle:
        handle.write(payload)
        tmp_path = Path(handle.name)
    shutil.move(str(tmp_path), str(destination))
    return destination
