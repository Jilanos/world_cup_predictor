"""Rolling (sequential) Elo ratings computed from historical results.

Elo is updated match by match in chronological order. For every match we record
the teams' ratings **before** that match — those pre-match ratings are leak-free
features for training. After processing all results, the final ratings are the
best available estimate for upcoming fixtures.

This replaces the previous approach, which neutralised the Elo signal during
training (so the model never learned from it). The Elo update is inherently
sequential, but it is a single O(n) pass — not the per-match O(n^2) recompute.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import ELO_HOME_ADVANTAGE, ELO_K

DEFAULT_BASE_ELO = 1500.0
DEFAULT_K = ELO_K
DEFAULT_HOME_ADVANTAGE = ELO_HOME_ADVANTAGE


@dataclass(frozen=True)
class EloResult:
    pre_match: pd.DataFrame  # columns: home_elo_pre, away_elo_pre (aligned to input index)
    final: dict[str, float]  # team -> latest rating


def _mov_multiplier(goal_diff: int) -> float:
    """Margin-of-victory multiplier (eloratings.net style)."""
    gd = abs(int(goal_diff))
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8.0


def _importance_weight(tournament: object) -> float:
    # Lazy import avoids a circular dependency with features.py.
    from .features import tournament_importance

    return tournament_importance(tournament)


def rolling_elo(
    results: pd.DataFrame,
    *,
    base: float = DEFAULT_BASE_ELO,
    k: float = DEFAULT_K,
    home_advantage: float = DEFAULT_HOME_ADVANTAGE,
) -> EloResult:
    """Compute pre-match Elo for every match and final ratings per team."""
    ordered = results.sort_values("date", kind="stable")
    ratings: dict[str, float] = {}

    home_pre = np.empty(len(ordered), dtype=float)
    away_pre = np.empty(len(ordered), dtype=float)

    has_neutral = "neutral" in ordered.columns
    has_tournament = "tournament" in ordered.columns

    home_teams = ordered["home_team"].to_numpy()
    away_teams = ordered["away_team"].to_numpy()
    home_scores = ordered["home_score"].to_numpy()
    away_scores = ordered["away_score"].to_numpy()
    neutrals = ordered["neutral"].to_numpy() if has_neutral else np.zeros(len(ordered))
    if has_tournament:
        importance = ordered["tournament"].map(_importance_weight).to_numpy(dtype=float)
    else:
        importance = np.ones(len(ordered))

    for i in range(len(ordered)):
        home = home_teams[i]
        away = away_teams[i]
        rh = ratings.get(home, base)
        ra = ratings.get(away, base)
        home_pre[i] = rh
        away_pre[i] = ra

        hfa = 0.0 if neutrals[i] else home_advantage
        expected_home = 1.0 / (1.0 + 10.0 ** ((ra - rh - hfa) / 400.0))

        hs = int(home_scores[i])
        as_ = int(away_scores[i])
        if hs > as_:
            actual_home = 1.0
        elif hs < as_:
            actual_home = 0.0
        else:
            actual_home = 0.5

        weight = k * importance[i] * _mov_multiplier(hs - as_)
        delta = weight * (actual_home - expected_home)
        ratings[home] = rh + delta
        ratings[away] = ra - delta

    pre = pd.DataFrame(
        {"home_elo_pre": home_pre, "away_elo_pre": away_pre}, index=ordered.index
    )
    return EloResult(pre_match=pre.reindex(results.index), final=ratings)
