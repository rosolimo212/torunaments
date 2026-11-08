# coding: utf-8
"""Хозяева поля, погода, состав и усталость.

Формула mu совпадает с tourn.get_match. Бонус хозяина прибавляется к mu
уже после неё. Состав сдвигает рейтинг до расчёта mu.
"""

import math
import random

import numpy as np

from tourn import elo_prob

MU_MULT = 100
MU_NORM = 15


def expected_mu(rating1, rating2):
    return MU_MULT * (elo_prob(rating1, rating2) - 0.5) / MU_NORM


def squad_shift(squad_percent, half_drop):
    """100% ничего не меняет. 50% даёт -half_drop пунктов рейтинга."""
    return (float(squad_percent) - 100.0) / 50.0 * float(half_drop)


def fatigue_mean_percent(games_played, tau):
    """Среднее состава в процентах. На нуле матчей это 100, пол — 50."""
    mean = 0.50 + 0.50 * math.exp(-float(games_played) / float(tau))
    return 100.0 * mean


def sample_fatigue_squad(games_played, tau, noise):
    value = random.gauss(fatigue_mean_percent(games_played, tau), float(noise))
    return min(100.0, max(0.0, value))


def weather_by_id(config):
    return {item["id"]: item for item in config["weather"]["states"]}


def draw_weather(config):
    states = weather_by_id(config)
    weights = config["weather"]["tournament_probabilities"]
    state_id = random.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]
    return states[state_id]


def describe_match(config, rating1, rating2, squad1=100, squad2=100, home=None, weather=None):
    """home: None, 'team1' или 'team2'. weather — словарь состояния или None (ясно)."""
    half_drop = config["match"]["squad_half_drop"]
    effective1 = float(rating1) + squad_shift(squad1, half_drop)
    effective2 = float(rating2) + squad_shift(squad2, half_drop)
    mu = expected_mu(effective1, effective2)
    home_mu = float(config["match"]["home_mu"])
    if home == "team1":
        mu = mu + home_mu
    elif home == "team2":
        mu = mu - home_mu
    if weather is None:
        weather = weather_by_id(config)["clear"]
    sigma = float(config["match"]["sigma"]) * (1.0 + float(weather["sigma_bonus"]))
    p_win, p_draw, p_loss = outcome_probabilities(mu, sigma)
    return {
        "mu": mu,
        "sigma": sigma,
        "p_win": p_win,
        "p_draw": p_draw,
        "p_loss": p_loss,
        "weather": weather["label"],
        "weather_id": weather["id"],
        "squad1": float(squad1),
        "squad2": float(squad2),
        "effective1": effective1,
        "effective2": effective2,
    }


def outcome_probabilities(mu, sigma):
    """Победа, ничья и поражение первой команды по нормальной разнице мячей.

    Победа — разница от +0.5, поражение — ниже −0.5, остальное ничья.
    """
    sigma = float(sigma)
    if sigma <= 0:
        raise ValueError("sigma должна быть положительной")
    p_loss = _normal_cdf((-0.5 - mu) / sigma)
    p_win = 1.0 - _normal_cdf((0.5 - mu) / sigma)
    p_draw = max(0.0, 1.0 - p_win - p_loss)
    return p_win, p_draw, p_loss


def _normal_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def sample_total(config):
    low = int(config["match"]["total_low"])
    high = int(config["match"]["total_high"])
    return int(np.random.randint(low, high + 1))


def sample_score(mu, sigma, total):
    """Та же генерация счёта, что в tourn.get_match, но с уже посчитанным mu."""
    base_res = np.round(random.normalvariate(mu, sigma), 0)
    if base_res > 0:
        return int(total + base_res), int(total)
    return int(total), int(total - base_res)


def play_match(config, rating1, rating2, squad1=100, squad2=100, home=None, weather=None):
    described = describe_match(config, rating1, rating2, squad1, squad2, home, weather)
    total = sample_total(config)
    score1, score2 = sample_score(described["mu"], described["sigma"], total)
    described["total"] = total
    described["score1"] = score1
    described["score2"] = score2
    return described
