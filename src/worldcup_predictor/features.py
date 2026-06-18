from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .elo import EloResult, rolling_elo


# Production model inputs. Phase 3 (AC3) removed `fifa_rank_diff`,
# `fifa_points_diff`, `market_home/draw/away`: those columns were constant at
# training time (no historical FIFA snapshots / odds), so the gradient-boosted
# model never split on them and its output was provably invariant to them, while
# real values were injected at fixture time. They were dead, misleading inputs.
# Market signal is applied as documented post-processing (`blend_with_market`),
# not as a model feature. The columns are still produced by the feature builders
# (the blend reads `market_*`), they are simply not fed to the model.
FEATURE_COLUMNS = [
    "elo_diff",
    "recent_form_5_diff",
    "recent_form_10_diff",
    "goals_for_pg_diff",
    "goals_against_pg_diff",
    "clean_sheet_rate_diff",
    "win_rate_diff",
    "neutral",
    "tournament_importance",
]

# Candidate draw/balance features (Phase 3 AC5). Experimental only: kept OUT of
# the production FEATURE_COLUMNS until a walk-forward ablation on the full
# dataset proves a robust log-loss/Brier gain. Use EXTENDED_FEATURE_COLUMNS to
# run that ablation.
BALANCE_FEATURE_COLUMNS = [
    "abs_elo_diff",
    "abs_recent_form_5_diff",
    "abs_recent_form_10_diff",
    "draw_rate_combined",
]

EXTENDED_FEATURE_COLUMNS = FEATURE_COLUMNS + BALANCE_FEATURE_COLUMNS

# Defaults used when a team has no prior matches.
_DEFAULT_FORM = 0.5
_DEFAULT_GOALS = 1.2
_DEFAULT_CLEAN_SHEET = 0.25
_DEFAULT_WIN_RATE = 0.33
_DEFAULT_DRAW_RATE = 0.25


@dataclass(frozen=True)
class TeamStats:
    form_5: float
    form_10: float
    goals_for_pg: float
    goals_against_pg: float
    clean_sheet_rate: float
    win_rate: float
    matches: int


def result_label(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home"
    if home_score < away_score:
        return "away"
    return "draw"


def _points_for(team_score: int, opp_score: int) -> int:
    if team_score > opp_score:
        return 3
    if team_score == opp_score:
        return 1
    return 0


def _team_match_rows(results: pd.DataFrame) -> pd.DataFrame:
    """Long table: two rows per match, one per team's perspective.

    Carries ``match_id`` (the source results index) so per-match home/away stats
    can be recombined after the rolling computation.
    """
    home = pd.DataFrame(
        {
            "match_id": results.index,
            "date": results["date"],
            "team": results["home_team"],
            "goals_for": results["home_score"],
            "goals_against": results["away_score"],
            "is_home": 1,
        }
    )
    away = pd.DataFrame(
        {
            "match_id": results.index,
            "date": results["date"],
            "team": results["away_team"],
            "goals_for": results["away_score"],
            "goals_against": results["home_score"],
            "is_home": 0,
        }
    )
    rows = pd.concat([home, away], ignore_index=True).sort_values(["team", "date"], kind="stable")
    rows["points"] = np.select(
        [rows["goals_for"] > rows["goals_against"], rows["goals_for"] == rows["goals_against"]],
        [3, 1],
        default=0,
    )
    rows["win"] = (rows["goals_for"] > rows["goals_against"]).astype(float)
    rows["clean_sheet"] = (rows["goals_against"] == 0).astype(float)
    rows["draw"] = (rows["goals_for"] == rows["goals_against"]).astype(float)
    return rows


def _trailing(group: "pd.core.groupby.SeriesGroupBy", window: int) -> pd.Series:
    """Mean over the previous ``window`` matches (excluding the current one)."""
    return group.transform(lambda s: s.shift(1).rolling(window, min_periods=1).mean())


def compute_team_stats_until(results: pd.DataFrame, as_of: pd.Timestamp) -> dict[str, TeamStats]:
    """Latest trailing stats per team using matches strictly before ``as_of``.

    Used for upcoming fixtures, where the most recent matches are all in the
    past, so the current match is *included* (no shift).
    """
    rows = _team_match_rows(results[results["date"] < as_of])
    stats: dict[str, TeamStats] = {}
    for team, group in rows.groupby("team", sort=False):
        group = group.sort_values("date", kind="stable")
        last_5 = group.tail(5)
        last_10 = group.tail(10)
        stats[team] = TeamStats(
            form_5=float(last_5["points"].mean() / 3) if len(last_5) else _DEFAULT_FORM,
            form_10=float(last_10["points"].mean() / 3) if len(last_10) else _DEFAULT_FORM,
            goals_for_pg=float(last_10["goals_for"].mean()) if len(last_10) else _DEFAULT_GOALS,
            goals_against_pg=float(last_10["goals_against"].mean()) if len(last_10) else _DEFAULT_GOALS,
            clean_sheet_rate=float(last_10["clean_sheet"].mean()) if len(last_10) else _DEFAULT_CLEAN_SHEET,
            win_rate=float(last_10["win"].mean()) if len(last_10) else _DEFAULT_WIN_RATE,
            matches=int(len(group)),
        )
    return stats


def _per_match_trailing_stats(results: pd.DataFrame) -> pd.DataFrame:
    """Vectorized leak-free trailing stats for every match in ``results``.

    Returns a frame indexed by the results index with home_*/away_* stat
    columns. Each match's stats use only that team's earlier matches (a single
    O(n log n) pass via groupby + shift + rolling, not a per-match recompute).
    """
    rows = _team_match_rows(results)
    grouped = rows.groupby("team", sort=False)

    rows["form_5"] = (_trailing(grouped["points"], 5) / 3).fillna(_DEFAULT_FORM)
    rows["form_10"] = (_trailing(grouped["points"], 10) / 3).fillna(_DEFAULT_FORM)
    rows["goals_for_pg"] = _trailing(grouped["goals_for"], 10).fillna(_DEFAULT_GOALS)
    rows["goals_against_pg"] = _trailing(grouped["goals_against"], 10).fillna(_DEFAULT_GOALS)
    rows["clean_sheet_rate"] = _trailing(grouped["clean_sheet"], 10).fillna(_DEFAULT_CLEAN_SHEET)
    rows["win_rate"] = _trailing(grouped["win"], 10).fillna(_DEFAULT_WIN_RATE)
    rows["draw_rate_10"] = _trailing(grouped["draw"], 10).fillna(_DEFAULT_DRAW_RATE)

    stat_columns = [
        "form_5",
        "form_10",
        "goals_for_pg",
        "goals_against_pg",
        "clean_sheet_rate",
        "win_rate",
        "draw_rate_10",
    ]
    home = rows[rows["is_home"] == 1].set_index("match_id")[stat_columns]
    away = rows[rows["is_home"] == 0].set_index("match_id")[stat_columns]
    combined = home.add_prefix("home_").join(away.add_prefix("away_"))
    return combined.reindex(results.index)


def tournament_importance(name: object) -> float:
    text = str(name).lower()
    if "world cup" in text:
        return 1.5
    if any(token in text for token in ["continental", "euro", "copa", "african cup", "asian cup", "gold cup"]):
        return 1.25
    if "friendly" in text:
        return 0.7
    if "qualification" in text or "qualifier" in text:
        return 1.1
    return 1.0


def training_matches(results: pd.DataFrame) -> pd.DataFrame:
    out = results.copy()
    out["tournament_importance"] = out["tournament"].map(tournament_importance).fillna(1.0)
    return out


def build_features_for_results(
    results: pd.DataFrame, elo_pre: pd.DataFrame | None = None, include_target: bool = True
) -> pd.DataFrame:
    """Leak-free per-match features for matches that are part of ``results``.

    Uses vectorized trailing form/goals and pre-match Elo. FIFA columns are
    neutral (no historical FIFA snapshots) and market columns are neutral
    (no historical odds); both are filled with the model's neutral priors.
    """
    if elo_pre is None:
        elo_pre = rolling_elo(results).pre_match

    stats = _per_match_trailing_stats(results)
    importance = results["tournament"].map(tournament_importance).fillna(1.0) if "tournament" in results else 1.0
    neutral = results["neutral"] if "neutral" in results else 0.0

    out = pd.DataFrame(index=results.index)
    out["date"] = results["date"]
    out["home_team"] = results["home_team"]
    out["away_team"] = results["away_team"]
    out["elo_diff"] = elo_pre["home_elo_pre"] - elo_pre["away_elo_pre"]
    out["fifa_rank_diff"] = 0.0
    out["fifa_points_diff"] = 0.0
    out["recent_form_5_diff"] = stats["home_form_5"] - stats["away_form_5"]
    out["recent_form_10_diff"] = stats["home_form_10"] - stats["away_form_10"]
    out["goals_for_pg_diff"] = stats["home_goals_for_pg"] - stats["away_goals_for_pg"]
    out["goals_against_pg_diff"] = stats["away_goals_against_pg"] - stats["home_goals_against_pg"]
    out["clean_sheet_rate_diff"] = stats["home_clean_sheet_rate"] - stats["away_clean_sheet_rate"]
    out["win_rate_diff"] = stats["home_win_rate"] - stats["away_win_rate"]
    out["neutral"] = neutral
    out["tournament_importance"] = importance
    out["market_home"] = 1 / 3
    out["market_draw"] = 1 / 3
    out["market_away"] = 1 / 3
    # Candidate draw/balance features (Phase 3 AC5, experimental). Derived from
    # already leak-free columns, so they inherit the no-future guarantee.
    out["abs_elo_diff"] = out["elo_diff"].abs()
    out["abs_recent_form_5_diff"] = out["recent_form_5_diff"].abs()
    out["abs_recent_form_10_diff"] = out["recent_form_10_diff"].abs()
    out["draw_rate_combined"] = (stats["home_draw_rate_10"] + stats["away_draw_rate_10"]) / 2
    if include_target:
        out["target"] = [
            result_label(int(h), int(a)) for h, a in zip(results["home_score"], results["away_score"])
        ]
    return out


def _rating_lookup(df: pd.DataFrame | None, value_column: str) -> dict[str, float]:
    if df is None or df.empty or value_column not in df.columns:
        return {}
    return df.set_index("team")[value_column].to_dict()


def build_fixture_features(
    fixtures: pd.DataFrame,
    results: pd.DataFrame,
    elo_final: dict[str, float] | None = None,
    manual_elo: pd.DataFrame | None = None,
    fifa: pd.DataFrame | None = None,
    odds: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Features for upcoming fixtures (not part of ``results``).

    Uses each team's latest trailing stats, manual Elo if provided else the
    rolling final Elo, optional manual FIFA ranks, and optional market odds.
    """
    as_of = results["date"].max() + pd.Timedelta(days=1)
    stats = compute_team_stats_until(results, as_of)
    default_stats = TeamStats(
        _DEFAULT_FORM, _DEFAULT_FORM, _DEFAULT_GOALS, _DEFAULT_GOALS, _DEFAULT_CLEAN_SHEET, _DEFAULT_WIN_RATE, 0
    )

    elo_lookup = _rating_lookup(manual_elo, "elo") or (dict(elo_final) if elo_final else {})
    default_elo = float(np.mean(list(elo_lookup.values()))) if elo_lookup else 1500.0
    fifa_rank_lookup = _rating_lookup(fifa, "rank")
    fifa_points_lookup = _rating_lookup(fifa, "points")
    default_rank = float(np.mean(list(fifa_rank_lookup.values()))) if fifa_rank_lookup else 100.0
    default_points = float(np.nanmean(list(fifa_points_lookup.values()))) if fifa_points_lookup else 0.0
    if np.isnan(default_points):
        default_points = 0.0

    odds_lookup: dict = {}
    if odds is not None and not odds.empty:
        keyed = odds.copy()
        keyed["key"] = list(zip(keyed["date"].dt.date, keyed["home_team"], keyed["away_team"]))
        odds_lookup = keyed.set_index("key")[["market_home", "market_draw", "market_away"]].to_dict("index")

    rows = []
    for _, match in fixtures.sort_values("date", kind="stable").iterrows():
        home = match["home_team"]
        away = match["away_team"]
        hs = stats.get(home, default_stats)
        as_s = stats.get(away, default_stats)
        market = odds_lookup.get((match["date"].date(), home, away), {})
        rows.append(
            {
                "date": match["date"],
                "home_team": home,
                "away_team": away,
                "elo_diff": float(elo_lookup.get(home, default_elo) - elo_lookup.get(away, default_elo)),
                "fifa_rank_diff": float(
                    fifa_rank_lookup.get(away, default_rank) - fifa_rank_lookup.get(home, default_rank)
                ),
                "fifa_points_diff": float(
                    fifa_points_lookup.get(home, default_points) - fifa_points_lookup.get(away, default_points)
                ),
                "recent_form_5_diff": hs.form_5 - as_s.form_5,
                "recent_form_10_diff": hs.form_10 - as_s.form_10,
                "goals_for_pg_diff": hs.goals_for_pg - as_s.goals_for_pg,
                "goals_against_pg_diff": as_s.goals_against_pg - hs.goals_against_pg,
                "clean_sheet_rate_diff": hs.clean_sheet_rate - as_s.clean_sheet_rate,
                "win_rate_diff": hs.win_rate - as_s.win_rate,
                "neutral": float(match.get("neutral", 0)),
                "tournament_importance": float(match.get("tournament_importance", 1.0)),
                "market_home": float(market.get("market_home", np.nan)),
                "market_draw": float(market.get("market_draw", np.nan)),
                "market_away": float(market.get("market_away", np.nan)),
            }
        )
    return pd.DataFrame(rows)
