from __future__ import annotations

import pandas as pd

from worldcup_predictor.elo import DEFAULT_BASE_ELO, rolling_elo


def _match(date, home, away, hs, as_, neutral=1, tournament="Friendly"):
    return {
        "date": pd.Timestamp(date),
        "home_team": home,
        "away_team": away,
        "home_score": hs,
        "away_score": as_,
        "neutral": neutral,
        "tournament": tournament,
    }


def _results(rows):
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def test_first_match_pre_elo_is_base():
    results = _results([_match("2020-01-01", "A", "B", 2, 0)])
    elo = rolling_elo(results)
    assert elo.pre_match.loc[0, "home_elo_pre"] == DEFAULT_BASE_ELO
    assert elo.pre_match.loc[0, "away_elo_pre"] == DEFAULT_BASE_ELO


def test_winner_gains_loser_loses_zero_sum():
    results = _results([_match("2020-01-01", "A", "B", 3, 0)])
    elo = rolling_elo(results)
    assert elo.final["A"] > DEFAULT_BASE_ELO
    assert elo.final["B"] < DEFAULT_BASE_ELO
    # Elo is zero-sum on a single match.
    gain = elo.final["A"] - DEFAULT_BASE_ELO
    loss = DEFAULT_BASE_ELO - elo.final["B"]
    assert gain == loss


def test_pre_match_elo_has_no_leakage():
    """A match's own result must not affect its pre-match rating, and must not
    affect any earlier match's pre-match rating."""
    base_rows = [
        _match("2020-01-01", "A", "B", 1, 0),
        _match("2020-02-01", "A", "C", 2, 1),
        _match("2020-03-01", "B", "C", 0, 0),
    ]
    flipped = [dict(r) for r in base_rows]
    flipped[2]["home_score"], flipped[2]["away_score"] = 4, 0  # change last match only

    base = rolling_elo(_results(base_rows)).pre_match
    after = rolling_elo(_results(flipped)).pre_match

    # The changed match is last; its own and all earlier pre-match ratings
    # are identical regardless of its outcome.
    pd.testing.assert_frame_equal(base, after)


def test_home_advantage_changes_expectation():
    home_rows = _results([_match("2020-01-01", "A", "B", 1, 1, neutral=0)])
    neutral_rows = _results([_match("2020-01-01", "A", "B", 1, 1, neutral=1)])
    # On a draw, the home team (favoured by HFA) should lose a little rating at
    # home but stay flat on neutral ground.
    home_final = rolling_elo(home_rows).final["A"]
    neutral_final = rolling_elo(neutral_rows).final["A"]
    assert home_final < neutral_final
    assert neutral_final == DEFAULT_BASE_ELO


def test_margin_of_victory_scales_update():
    small = rolling_elo(_results([_match("2020-01-01", "A", "B", 1, 0)])).final["A"]
    big = rolling_elo(_results([_match("2020-01-01", "A", "B", 5, 0)])).final["A"]
    assert big > small
