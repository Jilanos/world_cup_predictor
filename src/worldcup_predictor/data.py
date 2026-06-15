from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .team_aliases import normalize_team_name


def read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def normalize_team_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[column] = out[column].map(normalize_team_name)
    return out


def load_fixtures(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"date", "home_team", "away_team"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Fixtures file is missing columns: {sorted(missing)}")

    df = normalize_team_columns(df, ["home_team", "away_team"])
    df["date"] = pd.to_datetime(df["date"])
    if "neutral" not in df.columns:
        df["neutral"] = 1
    if "tournament_importance" not in df.columns:
        df["tournament_importance"] = 1.0
    return df


def load_results(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"date", "home_team", "away_team", "home_score", "away_score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Results file is missing columns: {sorted(missing)}")

    df = normalize_team_columns(df, ["home_team", "away_team"])
    df["date"] = pd.to_datetime(df["date"])
    if "neutral" not in df.columns:
        df["neutral"] = 0
    if "tournament" not in df.columns:
        df["tournament"] = "Unknown"
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")
    df = df.dropna(subset=["date", "home_team", "away_team", "home_score", "away_score"])
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    return df.sort_values("date").reset_index(drop=True)


def load_elo(path: Path) -> pd.DataFrame | None:
    df = read_csv_if_exists(path)
    if df is None:
        return None
    required = {"team", "elo"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Elo file is missing columns: {sorted(missing)}")
    df = normalize_team_columns(df, ["team"])
    df["elo"] = pd.to_numeric(df["elo"], errors="coerce")
    return df.dropna(subset=["team", "elo"])[["team", "elo"]]


def load_fifa(path: Path) -> pd.DataFrame | None:
    df = read_csv_if_exists(path)
    if df is None:
        return None
    required = {"team", "rank"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"FIFA rankings file is missing columns: {sorted(missing)}")
    df = normalize_team_columns(df, ["team"])
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    if "points" in df.columns:
        df["points"] = pd.to_numeric(df["points"], errors="coerce")
    else:
        df["points"] = np.nan
    return df.dropna(subset=["team", "rank"])[["team", "rank", "points"]]


def load_odds(path: Path) -> pd.DataFrame | None:
    df = read_csv_if_exists(path)
    if df is None:
        return None
    required = {"date", "home_team", "away_team", "home_odds", "draw_odds", "away_odds"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Odds file is missing columns: {sorted(missing)}")

    df = normalize_team_columns(df, ["home_team", "away_team"])
    df["date"] = pd.to_datetime(df["date"])
    for column in ["home_odds", "draw_odds", "away_odds"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["home_odds", "draw_odds", "away_odds"])
    implied = 1 / df[["home_odds", "draw_odds", "away_odds"]]
    overround = implied.sum(axis=1)
    df["market_home"] = implied["home_odds"] / overround
    df["market_draw"] = implied["draw_odds"] / overround
    df["market_away"] = implied["away_odds"] / overround
    return df
