# coding: utf-8
"""Текстовые таблицы и протокол матчей."""

import pandas as pd

from core.simulate import playoff_notes

COLUMN_NAMES = {
    "place": "Место",
    "team_name": "Команда",
    "games": "Игры",
    "footbal_points": "Очки",
    "wins": "Победы",
    "draws": "Ничьи",
    "loses": "Поражения",
    "scored": "Забитые",
    "mised": "Пропущенные",
    "goals_difference": "Разница",
    "outcome": "Итог",
    "path": "Путь",
}


MATCH_COLUMNS = [
    "Команда 1",
    "Счёт 1",
    "Счёт 2",
    "Команда 2",
    "Тур",
    "Готовность 1",
    "Готовность 2",
    "Погода",
    "Серия пенальти",
]


def match_rows(log, mode):
    tours = _tour_numbers(log)
    rows = []
    for index, row in enumerate(log.itertuples(index=False)):
        weather = getattr(row, "weather", "")
        rows.append({
            "Команда 1": row.team0_name,
            "Счёт 1": int(row.score0),
            "Счёт 2": int(row.score1),
            "Команда 2": row.team1_name,
            "Тур": tours[index],
            "Готовность 1": _readiness(row, "squad0"),
            "Готовность 2": _readiness(row, "squad1"),
            "Погода": str(weather) if weather else "—",
            "Серия пенальти": "да" if _went_to_penalties(row, mode) else "нет",
        })
    frame = pd.DataFrame(rows, columns=MATCH_COLUMNS)
    frame["Тур"] = frame["Тур"].astype("Int64")
    return frame


def _readiness(row, field):
    value = getattr(row, field, None)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    return f"{float(value):.0f}%"


def _went_to_penalties(row, mode):
    if int(row.score0) != int(row.score1):
        return False
    if mode == "playoff":
        return True
    return getattr(row, "stage", None) == "second_stage"


def _tour_numbers(log):
    """Номер тура. В плей-офф и швейцарке он уже в протоколе.

    Круговая часть номера тура не хранит: пары идут по кругам в том же порядке,
    в каком их собрал календарь. Группы в комбинированном турнире не пересекаются,
    поэтому номер восстанавливается внутри каждой группы.
    """
    tours = [pd.NA] * len(log)
    missing = []
    for index, row in enumerate(log.itertuples(index=False)):
        rnd = getattr(row, "round", None)
        if rnd is not None and not (isinstance(rnd, float) and pd.isna(rnd)):
            tours[index] = int(rnd)
        else:
            missing.append(index)
    if not missing:
        return tours

    parent = {}

    def find(team):
        parent.setdefault(team, team)
        while parent[team] != team:
            parent[team] = parent[parent[team]]
            team = parent[team]
        return team

    def unite(left, right):
        left, right = find(left), find(right)
        if left != right:
            parent[right] = left

    ids = list(zip(log["id0"].tolist(), log["id1"].tolist()))
    for index in missing:
        unite(int(ids[index][0]), int(ids[index][1]))
    groups = {}
    for index in missing:
        groups.setdefault(find(int(ids[index][0])), []).append(index)
    for indexes in groups.values():
        teams = set()
        for index in indexes:
            teams.add(int(ids[index][0]))
            teams.add(int(ids[index][1]))
        per_round = max(len(teams) // 2, 1)
        for order, index in enumerate(indexes):
            tours[index] = order // per_round + 1
    return tours


def standings_frame(result):
    table = result["table"].copy()
    table["team_id"] = table["team_id"].astype(int)
    mode = result["mode"]
    columns = ["place", "team_name", "scored", "mised", "goals_difference"]
    if mode in ("round_robin", "swiss", "combine"):
        columns = [
            "place", "team_name", "games", "footbal_points", "wins", "draws", "loses",
            "scored", "mised", "goals_difference",
        ]
    if mode == "playoff":
        notes = playoff_notes(result["log"])
        table = _merge_notes(table, notes)
        columns = ["place", "team_name", "outcome", "scored", "mised", "goals_difference", "path"]
    elif mode == "combine":
        notes = playoff_notes(result["log"], stage="second_stage")
        table = _merge_notes(table, notes)
        columns = columns + ["outcome", "path"]
    view = table[columns].copy()
    for column in ("place", "games", "footbal_points", "wins", "draws", "loses", "scored", "mised", "goals_difference"):
        if column in view.columns:
            view[column] = view[column].round().astype("Int64")
    view = view.rename(columns=COLUMN_NAMES)
    return view.sort_values("Место")


def _merge_notes(table, notes):
    if notes.empty:
        table["path"] = ""
        table["outcome"] = ""
        return table
    notes = notes.copy()
    notes["team_id"] = notes["team_id"].astype(int)
    merged = table.merge(notes, on="team_id", how="left")
    merged["path"] = merged["path"].fillna("")
    merged["outcome"] = merged["outcome"].fillna("")
    return merged
