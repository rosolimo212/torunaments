# coding: utf-8
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import load_config
from core.simulate import run_tournament
from core.teams import catalog_from_config, preset_frame, teams_dict_from_frame
from ui.charts import DRAW_COLOR, LOSS_COLOR, WIN_COLOR, goal_diff_chart, place_heatmap
from ui.present import match_rows


def _teams(n):
    config = load_config()
    catalog = catalog_from_config(config)
    frame = preset_frame(catalog, {"kind": "top", "n": n, "label": "t"})
    return config, teams_dict_from_frame(frame)


def test_round_robin_tours_and_no_penalties():
    config, teams = _teams(4)
    params = {"cycles": 2, "rounds": 3, "groups": 2, "promote": 2, "seed": "half"}
    result = run_tournament(teams, config, "round_robin", params, False, False)
    rows = match_rows(result["log"], "round_robin")
    assert list(rows.columns)[:5] == ["Команда 1", "Счёт 1", "Счёт 2", "Команда 2", "Тур"]
    assert rows.groupby("Тур").size().tolist() == [2, 2, 2, 2, 2, 2]
    for _tour, part in rows.groupby("Тур"):
        names = part["Команда 1"].tolist() + part["Команда 2"].tolist()
        assert len(names) == len(set(names))
    assert set(rows["Серия пенальти"]) == {"нет"}
    assert set(rows["Погода"]) == {"—"}
    assert set(rows["Готовность 1"]) == {"100%"}


def test_playoff_draw_is_a_shootout():
    log = pd.DataFrame([{
        "id0": 1, "id1": 2, "score0": 1, "score1": 1,
        "team0_name": "А", "team1_name": "Б", "round": 1,
        "squad0": 90, "squad1": 80, "weather": "Сильный дождь",
    }, {
        "id0": 1, "id1": 2, "score0": 2, "score1": 0,
        "team0_name": "А", "team1_name": "Б", "round": 2,
        "squad0": 90, "squad1": 80, "weather": "Ясно",
    }])
    rows = match_rows(log, "playoff")
    assert rows["Серия пенальти"].tolist() == ["да", "нет"]
    assert rows["Готовность 1"].tolist() == ["90%", "90%"]
    assert rows["Погода"].tolist() == ["Сильный дождь", "Ясно"]


def test_goal_diff_colors_name_the_favorite():
    figure = goal_diff_chart([2, 0, -3], "Арсенал", "Реал")
    bars = figure.data[0]
    assert list(bars.marker.color) == [LOSS_COLOR, DRAW_COLOR, WIN_COLOR]
    assert list(bars.customdata) == [
        "Разница 3: в пользу Реал",
        "Разница 0: ничья",
        "Разница 2: в пользу Арсенал",
    ]


def test_heatmap_cells_are_square_and_diagonal_is_labeled():
    rows = []
    for iteration in range(5):
        for team, rating, place in (("А", 3, 1), ("Б", 2, 2), ("В", 1, 3)):
            rows.append({
                "iteration": iteration, "team_id": place, "team_name": team,
                "started_rating": rating, "place": place,
            })
    figure = place_heatmap(pd.DataFrame(rows))
    width = figure.layout.width - figure.layout.margin.l - figure.layout.margin.r
    height = figure.layout.height - figure.layout.margin.t - figure.layout.margin.b
    assert width == height
    assert list(figure.layout.xaxis.range) == [-0.5, 2.5]
    assert list(figure.layout.yaxis.range) == [2.5, -0.5]
    labels = {(item.x, item.y): item.text for item in figure.layout.annotations}
    assert labels[(0, "А")] == "100%"
    assert labels[(1, "Б")] == "100%"
    assert labels[(2, "В")] == "100%"
