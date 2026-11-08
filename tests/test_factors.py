# coding: utf-8
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import load_config
from core.factors import (
    describe_match,
    expected_mu,
    fatigue_mean_percent,
    outcome_probabilities,
    squad_shift,
)
from core.simulate import run_tournament, validate_tournament
from core.teams import catalog_from_config, preset_frame, teams_dict_from_frame
from tourn import elo_prob


def test_mu_matches_library_formula():
    rating1, rating2 = 2100, 1900
    manual = 100 * (elo_prob(rating1, rating2) - 0.5) / 15
    assert expected_mu(rating1, rating2) == manual


def test_home_bonus_and_squad_shift():
    config = load_config()
    neutral = describe_match(config, 2000, 2000)
    home = describe_match(config, 2000, 2000, home="team1")
    away = describe_match(config, 2000, 2000, home="team2")
    assert home["mu"] == neutral["mu"] + config["match"]["home_mu"]
    assert away["mu"] == neutral["mu"] - config["match"]["home_mu"]
    assert squad_shift(100, 241) == 0
    assert squad_shift(50, 241) == -241
    assert squad_shift(0, 241) == -482
    weakened = describe_match(config, 2000, 2000, squad1=50)
    assert weakened["effective1"] == 2000 - 241


def test_weather_multiplies_sigma():
    config = load_config()
    clear = describe_match(config, 1800, 1800, weather={"id": "clear", "label": "Ясно", "sigma_bonus": 0})
    rain = describe_match(config, 1800, 1800, weather={"id": "heavy_rain", "label": "Сильный дождь", "sigma_bonus": 0.15})
    wind = describe_match(config, 1800, 1800, weather={"id": "strong_wind", "label": "Сильный ветер", "sigma_bonus": 0.05})
    assert abs(clear["sigma"] - config["match"]["sigma"]) < 1e-12
    assert abs(rain["sigma"] - config["match"]["sigma"] * 1.15) < 1e-12
    assert abs(wind["sigma"] - config["match"]["sigma"] * 1.05) < 1e-12


def test_fatigue_curve():
    assert fatigue_mean_percent(0, 150) == 100
    after_15 = fatigue_mean_percent(15, 150)
    assert abs(after_15 - (50 + 50 * math.exp(-0.1))) < 1e-9
    assert 94 < after_15 < 96
    assert fatigue_mean_percent(300, 150) > 50
    assert fatigue_mean_percent(300, 150) < 60
    assert fatigue_mean_percent(10000, 150) == 50


def test_outcome_probabilities_sum_and_symmetry():
    p_win, p_draw, p_loss = outcome_probabilities(0, 2.5)
    assert abs(p_win + p_draw + p_loss - 1) < 1e-12
    assert abs(p_win - p_loss) < 1e-12
    strong, _draw, weak = outcome_probabilities(2, 2.5)
    assert strong > weak


def test_presets_and_short_tournaments():
    config = load_config()
    catalog = catalog_from_config(config)
    top8 = preset_frame(catalog, config["presets"][0])
    assert len(top8) == 8
    assert top8["opta_rank"].min() == 1
    league = preset_frame(catalog, next(item for item in config["presets"] if item["id"] == "epl"))
    assert len(league) == 20
    teams = teams_dict_from_frame(top8)
    circle = run_tournament(teams, config, "round_robin", {"cycles": 1}, weather_on=True, fatigue_on=True)
    assert len(circle["log"]) == 28
    assert len(circle["log"]) == len(circle["table"]) * 28 / 8
    assert set(circle["table"]["place"]) == set(range(1, 9))
    playoff = run_tournament(teams, config, "playoff", {"seed": "half"}, weather_on=False, fatigue_on=False)
    assert playoff["table"]["place"].nunique() == 8
    swiss = run_tournament(teams, config, "swiss", {"rounds": 3}, weather_on=False, fatigue_on=True)
    assert int(swiss["log"]["round"].max()) == 3
    assert len(swiss["log"]) == 12


def test_odd_swiss_is_rejected():
    try:
        validate_tournament(7, "swiss", {"rounds": 3})
    except ValueError as error:
        assert "чётн" in str(error)
    else:
        raise AssertionError("odd swiss should fail")


def test_group_needs_two_teams():
    try:
        validate_tournament(5, "combine", {"groups": 3, "promote": 1, "cycles": 1})
    except ValueError as error:
        assert "две команды" in str(error)
    else:
        raise AssertionError("tiny groups should fail")
