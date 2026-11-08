# coding: utf-8
"""Турниры и серии матчей для веб-интерфейса.

Расписание, жеребьёвка и таблица берутся из tourn.py.
Счёт каждого матча считает core.factors, чтобы учесть погоду и усталость.
"""

import math

import numpy as np
import pandas as pd

import tourn
from core.factors import draw_weather, play_match, sample_fatigue_squad


class MatchPlayer:
    """Колбэк для tourn.simulate_*. Запоминает погоду и состав каждого матча.

    Швейцарка может выбросить неудачную жеребьёвку. begin_attempt / abort_attempt
    откатывают и протокол, и счётчик сыгранных матчей.
    """

    def __init__(self, teams_dct, config, weather_on, fatigue_on):
        self.teams = teams_dct
        self.config = config
        self.weather_on = weather_on
        self.fatigue_on = fatigue_on
        self.rows = []
        self.games = {team_id: 0 for team_id in teams_dct}
        self._snap_rows = None
        self._snap_games = None

    def begin_attempt(self):
        self._snap_rows = list(self.rows)
        self._snap_games = dict(self.games)

    def abort_attempt(self):
        if self._snap_rows is None:
            return
        self.rows = self._snap_rows
        self.games = self._snap_games

    def __call__(self, team0, team1):
        team0 = int(team0)
        team1 = int(team1)
        if self.fatigue_on:
            squad0 = sample_fatigue_squad(
                self.games[team0], self.config["match"]["fatigue_tau"], self.config["match"]["fatigue_noise"],
            )
            squad1 = sample_fatigue_squad(
                self.games[team1], self.config["match"]["fatigue_tau"], self.config["match"]["fatigue_noise"],
            )
        else:
            squad0 = 100.0
            squad1 = 100.0
        weather = draw_weather(self.config) if self.weather_on else None
        info0 = self.teams[team0]
        info1 = self.teams[team1]
        played = play_match(
            self.config,
            info0["start_rating"],
            info1["start_rating"],
            squad1=squad0,
            squad2=squad1,
            home=None,
            weather=weather,
        )
        self.rows.append({
            "mu": played["mu"],
            "sigma": played["sigma"],
            "weather": played["weather"] if self.weather_on else "",
            "squad0": played["squad1"],
            "squad1": played["squad2"],
        })
        self.games[team0] = self.games[team0] + 1
        self.games[team1] = self.games[team1] + 1
        return played["score1"], played["score2"]


def run_match_series(config, rating1, rating2, squad1, squad2, home, weather, n, progress=None):
    diffs = []
    wins = draws = 0
    for index in range(n):
        played = play_match(config, rating1, rating2, squad1, squad2, home, weather)
        diff = played["score1"] - played["score2"]
        diffs.append(diff)
        if diff > 0:
            wins += 1
        elif diff == 0:
            draws += 1
        if progress is not None:
            progress(index + 1, n)
    return {
        "diffs": diffs,
        "p_win": wins / n,
        "p_draw": draws / n,
        "p_loss": (n - wins - draws) / n,
    }


def validate_tournament(n_teams, mode, params):
    if n_teams < 2:
        raise ValueError("Нужны хотя бы две команды.")
    if mode == "swiss" and n_teams % 2 != 0:
        raise ValueError("В швейцарке нужно чётное число команд.")
    if mode == "swiss" and int(params["rounds"]) < 1:
        raise ValueError("Нужен хотя бы один тур.")
    if mode == "round_robin" and int(params["cycles"]) < 1:
        raise ValueError("Нужен хотя бы один круг.")
    if mode == "combine":
        groups = int(params["groups"])
        promote = int(params["promote"])
        cycles = int(params["cycles"])
        if groups < 1:
            raise ValueError("Нужна хотя бы одна группа.")
        if cycles < 1:
            raise ValueError("В группе нужен хотя бы один круг.")
        if promote < 1:
            raise ValueError("Из группы должна выходить хотя бы одна команда.")
        size = math.ceil(n_teams / groups)
        lengths = []
        for index in range(groups):
            start = index * size
            end = min(n_teams, (index + 1) * size)
            if end > start:
                lengths.append(end - start)
        if any(length < 2 for length in lengths):
            raise ValueError("В каждой группе нужно хотя бы две команды. Уменьшите число групп.")
        advancing = sum(min(promote, length) for length in lengths)
        if advancing < 2:
            raise ValueError("В плей-офф должны выходить хотя бы две команды.")


def run_tournament(teams_dct, config, mode, params, weather_on, fatigue_on):
    validate_tournament(len(teams_dct), mode, params)

    player = MatchPlayer(teams_dct, config, weather_on, fatigue_on)
    total = (config["match"]["total_low"], config["match"]["total_high"])
    sigma = (config["match"]["sigma"], config["match"]["sigma"])

    if mode == "round_robin":
        schedule = tourn.get_round_robin_schedule(teams_dct, num_cycles=int(params["cycles"]))
        log = tourn.simulate_matches_by_schedule(
            teams_dct, schedule, total=total, sigma=sigma, play_match=player,
        )
        table = tourn.make_res_table(log, teams_dct)
        table["place"] = table["roundrobin_place"]
    elif mode == "playoff":
        log = tourn.simulate_playoff_tourn(
            teams_dct, seed_mode=params["seed"], total=total, sigma=sigma, play_match=player,
        )
        table = tourn.make_res_table(log, teams_dct)
        table["place"] = table["playoff_place"]
    elif mode == "swiss":
        log, _swiss = tourn.simulate_swiss_tourn(
            teams_dct,
            n_rounds=int(params["rounds"]),
            total=total,
            sigma=sigma,
            play_match=player,
        )
        table = tourn.make_res_table(log, teams_dct)
        table["place"] = table["swiss_place"]
    elif mode == "combine":
        log, table = tourn.simulatate_combine_tournament(
            teams_dct,
            total=total,
            sigma=sigma,
            first_step_tourn_mode="round_robin",
            first_step_number_param=int(params["cycles"]),
            first_step_groups=int(params["groups"]),
            first_step_teams_to_promote=int(params["promote"]),
            second_step_string_param=params["seed"],
            play_match=player,
        )
        table["place"] = table["combined_place"]
    else:
        raise ValueError("Неизвестный формат турнира.")

    if len(player.rows) != len(log):
        raise RuntimeError("Протокол факторов не совпал с числом матчей.")
    log = log.reset_index(drop=True)
    context = pd.DataFrame(player.rows)
    for column in context.columns:
        log[column] = context[column].values
    table = table.sort_values(["place", "team_name"]).reset_index(drop=True)
    return {"log": log, "table": table, "mode": mode}


def run_tournament_series(teams_dct, config, mode, params, weather_on, fatigue_on, n, progress=None):
    parts = []
    for index in range(n):
        one = run_tournament(teams_dct, config, mode, params, weather_on, fatigue_on)
        part = one["table"][["team_id", "team_name", "started_rating", "place"]].copy()
        part["iteration"] = index
        parts.append(part)
        if progress is not None:
            progress(index + 1, n)
    return pd.concat(parts, ignore_index=True)


def place_matrix(place_df):
    """Доли итераций: строки — команды по убыванию рейтинга, столбцы — места."""
    normalized = int(place_df["iteration"].max()) + 1
    grouped = (
        place_df.groupby(["team_name", "started_rating", "place"], as_index=False)
        .size()
        .rename(columns={"size": "iterations"})
    )
    pivot = grouped.pivot_table(
        index=["started_rating", "team_name"],
        columns="place",
        values="iterations",
        fill_value=0,
    )
    pivot = pivot.reindex(columns=sorted(pivot.columns))
    pivot = pivot.sort_index(level="started_rating", ascending=False)
    shares = pivot / normalized
    return shares, normalized


def justice_index(place_df):
    """Та же формула, что в tourn.get_multiverse_stat, без графика."""
    normalized = int(place_df["iteration"].max()) + 1
    ranks = place_df[["team_id", "started_rating"]].drop_duplicates()
    ranks = ranks.copy()
    ranks["true_place"] = ranks["started_rating"].rank(method="dense", ascending=False).astype(int)
    grouped = (
        place_df.groupby(["team_id", "started_rating", "place"], as_index=False)
        .agg(iterations=("iteration", "nunique"))
    )
    grouped = grouped.merge(ranks[["team_id", "true_place"]], on="team_id", how="left")
    grouped["weight"] = np.exp(1 / grouped["true_place"])
    diagonal = grouped[grouped["place"] == grouped["true_place"]]
    if diagonal.empty:
        return 0.0
    value = diagonal["iterations"] / normalized
    return float((value * diagonal["weight"]).sum() / diagonal["weight"].sum())


def favorite_win_probability(place_df):
    """Вероятность первого места у команды с самым высоким рейтингом."""
    ranks = place_df.groupby(["team_id", "team_name"], as_index=False)["started_rating"].max()
    top = float(ranks["started_rating"].max())
    favorites = ranks[np.isclose(ranks["started_rating"], top)]
    n = place_df["iteration"].nunique()
    rows = []
    for favorite in favorites.itertuples(index=False):
        team_rows = place_df[place_df["team_id"] == favorite.team_id]
        wins = int((team_rows["place"] == 1).sum())
        rows.append({
            "team_name": favorite.team_name,
            "started_rating": favorite.started_rating,
            "probability": wins / n,
        })
    return rows


def round_name(teams_playing):
    if teams_playing <= 2:
        return "финал"
    return "1/" + str(teams_playing // 2)


def playoff_notes(log, stage=None):
    """Путь по сетке и итог для каждой команды."""
    work = log
    if stage is not None and "stage" in log.columns:
        work = log[log["stage"] == stage]
    if work.empty or "round" not in work.columns:
        return pd.DataFrame(columns=["team_id", "path", "outcome"])

    labels = {}
    for rnd, part in work.groupby("round"):
        labels[int(rnd)] = round_name(len(part) * 2)

    pieces = []
    for row in work.itertuples(index=False):
        rnd = int(row.round)
        label = labels.get(rnd, "тур " + str(rnd))
        pen = " (пенальти)" if int(row.score0) == int(row.score1) else ""
        pieces.append({
            "team_id": row.id0,
            "round": rnd,
            "text": f"{label}: {row.team1_name} {int(row.score0)}:{int(row.score1)}{pen}",
            "won": int(row.score0) > int(row.score1) or (
                int(row.score0) == int(row.score1) and int(getattr(row, "penalty_case", 0)) == 1
            ),
        })
        pen = " (пенальти)" if int(row.score0) == int(row.score1) else ""
        pieces.append({
            "team_id": row.id1,
            "round": rnd,
            "text": f"{label}: {row.team0_name} {int(row.score1)}:{int(row.score0)}{pen}",
            "won": int(row.score1) > int(row.score0) or (
                int(row.score0) == int(row.score1) and int(getattr(row, "penalty_case", 0)) == 0
            ),
        })
    path_df = pd.DataFrame(pieces).sort_values(["team_id", "round"])
    last_round = int(work["round"].max())
    rows = []
    for team_id, part in path_df.groupby("team_id"):
        last = part.iloc[-1]
        if int(last["round"]) == last_round and bool(last["won"]):
            outcome = "чемпион"
        else:
            outcome = "вылет в " + labels.get(int(last["round"]), "туре " + str(int(last["round"])))
        rows.append({
            "team_id": team_id,
            "path": "; ".join(part["text"].tolist()),
            "outcome": outcome,
        })
    return pd.DataFrame(rows)


def should_report(done, total):
    """Обновлять полосу примерно сто раз, а не на каждом шаге."""
    if done == total or done == 1:
        return True
    step = max(1, math.ceil(total / 100))
    return done % step == 0
