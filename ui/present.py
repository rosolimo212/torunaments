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


def match_rows(log, show_weather, show_squad):
    rows = []
    for row in log.itertuples(index=False):
        line = f"{row.team0_name} {int(row.score0)}:{int(row.score1)} {row.team1_name}"
        details = []
        stage = getattr(row, "stage", None)
        if stage == "first_stage":
            details.append("группа")
        elif stage == "second_stage":
            details.append("плей-офф")
        rnd = getattr(row, "round", None)
        if rnd is not None and not (isinstance(rnd, float) and pd.isna(rnd)):
            details.append("тур " + str(int(rnd)))
        weather = getattr(row, "weather", "")
        if show_weather and weather:
            details.append(str(weather))
        if show_squad:
            details.append(f"состав {float(row.squad0):.0f}% / {float(row.squad1):.0f}%")
        rows.append({"Матч": line, "Условия": ", ".join(details)})
    return pd.DataFrame(rows)


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
