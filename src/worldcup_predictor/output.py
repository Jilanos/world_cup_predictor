from __future__ import annotations

from pathlib import Path

import pandas as pd


OUTPUT_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "predicted_result",
    "predicted_winner_or_draw",
    "probability_home_win",
    "probability_draw",
    "probability_away_win",
    "confidence_level",
    "short_explanation",
]


def write_outputs(predictions: pd.DataFrame, csv_path: Path, md_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    predictions[OUTPUT_COLUMNS].to_csv(csv_path, index=False)
    md_path.write_text(to_markdown_table(predictions[OUTPUT_COLUMNS]), encoding="utf-8")


def to_markdown_table(df: pd.DataFrame) -> str:
    headers = list(df.columns)
    rows = [[str(value) for value in row] for row in df.to_numpy()]
    widths = [
        max(len(header), *(len(row[index]) for row in rows)) if rows else len(header)
        for index, header in enumerate(headers)
    ]
    header_line = "| " + " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)) + " |"
    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    body = [
        "| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(row)) + " |"
        for row in rows
    ]
    return "\n".join([header_line, separator, *body]) + "\n"
