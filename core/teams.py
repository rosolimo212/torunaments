# coding: utf-8
"""Каталог клубов Opta и пресеты."""

from functools import lru_cache

import pandas as pd

from core.config import ratings_path


@lru_cache(maxsize=4)
def load_catalog(path):
    frame = pd.read_csv(path)
    frame["team_id"] = frame["team_id"].astype(int)
    frame["start_rating"] = frame["start_rating"].astype(float)
    frame["opta_rating"] = frame["opta_rating"].astype(float)
    frame["opta_rank"] = frame["opta_rank"].astype(int)
    return frame.sort_values("opta_rank").reset_index(drop=True)


def catalog_from_config(config):
    return load_catalog(str(ratings_path(config)))


def preset_frame(catalog, preset):
    kind = preset["kind"]
    if kind == "top":
        return catalog.nsmallest(int(preset["n"]), "opta_rank").copy()
    if kind == "league":
        found = catalog[catalog["league"] == preset["league"]].copy()
        if found.empty:
            raise ValueError("В файле рейтингов нет лиги: " + preset["league"])
        return found.sort_values("opta_rank")
    if kind == "custom":
        return catalog.iloc[0:0].copy()
    raise ValueError("Неизвестный пресет: " + str(kind))


def teams_dict_from_frame(frame):
    """Словарь, который ждёт tourn.py. Ключ — team_id."""
    teams = {}
    for row in frame.itertuples(index=False):
        team_id = int(row.team_id)
        teams[team_id] = {
            "team_name": row.team_name,
            "start_rating": float(row.start_rating),
            "is_active": 1,
            "main_value": 0.0,
            "opta_rating": float(row.opta_rating),
        }
    return teams


def apply_rating_edits(frame, edited_ratings):
    """edited_ratings: список чисел в том же порядке, что и строки frame."""
    updated = frame.copy()
    updated["start_rating"] = [float(value) for value in edited_ratings]
    return updated
