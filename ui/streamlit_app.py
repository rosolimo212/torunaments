# coding: utf-8
"""Локальный интерфейс моделирования матчей и турниров.

Запуск из корня проекта:
    streamlit run ui/streamlit_app.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from core.config import load_config
from core.factors import describe_match, play_match, weather_by_id
from core.simulate import (
    favorite_win_probability,
    justice_index,
    run_match_series,
    run_tournament,
    run_tournament_series,
    should_report,
)
from core.teams import catalog_from_config, preset_frame, teams_dict_from_frame
from ui.charts import goal_diff_chart, place_heatmap
from ui.present import match_rows, standings_frame

HELP = {
    "team": "Клуб из рейтинга Opta. От него берётся сила команды. Её можно заменить числом ниже.",
    "rating": "Сила в модели. Около 100 пунктов — один мяч преимущества против равного соперника. Рядом серым написан исходный балл Opta от 0 до 100.",
    "squad": "100% — оптимальный состав. 50% ослабляет команду примерно на два мяча, если соперник равен по силе.",
    "venue": "По умолчанию поле нейтральное. Хозяева получают плюс 0,4 мяча к ожидаемой разнице. Бонус один на всех и задан в настройках.",
    "weather": "Ясно и слабый ветер не меняют случайность. Сильный ветер и слабый дождь расширяют разброс счёта на 5%, сильный дождь — на 15%.",
    "formula": "Три числа слева направо: победа первой команды, ничья, поражение первой. Это шансы по формуле, ещё до розыгрыша конкретного счёта.",
    "simulate_match": "Разыграть один случайный счёт при текущих силе, составе, поле и погоде.",
    "n_sims": "Сколько раз повторить один и тот же матч или турнир. Чем больше, тем ровнее проценты. Обычный выбор — 1000.",
    "simulate_matches": "Много независимых счётов. График показывает, как часто первая команда выигрывает в один мяч, в три, проигрывает и так далее.",
    "p_team": "Доля симуляций, в которых эта команда забила больше.",
    "p_draw": "Доля симуляций, которые закончились вничью.",
    "goal_chart": "Столбик — доля симуляций с такой разницей мячей. Зелёный — победа первой команды, жёлтый — ничья, красный — победа второй. Наведение показывает, в чью пользу разница.",
    "score": "Один случайный итог. Рядом те же mu и sigma, по которым он разыгран.",
    "mu": "Ожидаемая разница мячей в пользу первой команды. Положительное число — первая в среднем забивает больше.",
    "sigma": "Разброс счёта. При большой sigma аутсайдер чаще забирает очки.",
    "total": "Сколько голов забивает проигравший: 0 или 1. На разницу мячей это не влияет. 2:0 и 3:1 — одна и та же разница.",
    "p_formula": "Вероятность этого исхода по формуле. Это не доля из многих прогонов, а шанс ещё до жеребьёвки счёта.",
    "preset": "Готовый список клубов или свой набор. Топ мира и пять лиг взяты из рейтинга Opta.",
    "search": "Часть названия клуба. В списке ниже до 400 совпадений, уже выбранные команды остаются.",
    "custom_teams": "Кого включить в турнир. Нужны минимум две команды. Для швейцарки число команд должно быть чётным.",
    "club_name": "Название из рейтинга Opta. Если короткое имя встречается больше одного раза, рядом указана страна.",
    "model_rating": "Эту колонку можно править. Именно она идёт в симуляцию. Балл Opta при этом не меняется.",
    "opta": "Официальный балл Opta от 0 до 100. В модель он уже переведён: умножен на 24, чтобы 100 пунктов значили около одного мяча.",
    "format": "На вылет — проигравший выбывает, ничья решается пенальти с шансом 50 на 50. Круг — все играют со всеми, места по очкам. Группа и плей-офф — сначала группы, потом сетка. Швейцарка — в каждом туре соседи по таблице, команд должно быть чётное число.",
    "seed": "По рейтингу сильнейшие не встречаются до поздних раундов. Случайный посев заново тасует пары в каждом раунде.",
    "cycles": "Сколько раз каждая пара встречается. Два круга похожи на чемпионат дома и в гостях, но бонус хозяев здесь не включается.",
    "rounds": "Сколько матчей сыграет каждая команда. После неудачной жеребьёвки турнир собирается заново. Если пар без повторов уже нет, допускается повтор с самым редким соперником.",
    "groups": "На сколько групп делить список. В каждой группе должно остаться хотя бы две команды.",
    "promote": "Сколько первых мест группы выходят в плей-офф. В сетку должны попасть хотя бы две команды.",
    "group_cycles": "Сколько кругов играют внутри группы до плей-офф.",
    "tour_weather": "В каждом матче своя погода. Чаще всего ясно. Слабый ветер на счёт не влияет, но пишется в протоколе.",
    "fatigue": "Состав на матч случайный. В начале среднее 100%. С каждым сыгранным матчем среднее плавно снижается и подходит к 50%, но не опускается ниже.",
    "simulate_tournament": "Один розыгрыш: все матчи и итоговая таблица.",
    "simulate_tournaments": "Много розыгрышей одного и того же турнира. По ним строится карта мест и индекс справедливости.",
    "heatmap": "Строка — команда, столбец — место. Число в клетке — как часто команда занимала это место. Клетки квадратные. Жирнее подписана главная диагональ: команда на месте, которое соответствует её силе. Цвет тянется от самой редкой клетки к самой частой.",
    "justice": "Одно число: насколько места совпали с силой команд. 100% — сильнейший всегда первый, слабейший всегда последний. 0% — сила на итог не влияет. Считается по диагонали карты. Попадание в первое место весит чуть больше, чем в последнее.",
    "favorite": "Как часто команда с самым высоким рейтингом занимала первое место. Если таких команд несколько, доля показана для каждой.",
    "matches": "Протокол по одному матчу в строке: кто играл, счёт, тур, готовность состава, погода и была ли серия пенальти. Пенальти бывают только в плей-офф и только при ничьей.",
    "table": "Место, забитые, пропущенные и разница. В круге и швейцарке ещё игры и очки. В плей-офф — стадия вылета и путь по сетке.",
}


def main():
    config = load_config()
    st.set_page_config(page_title=config["app"]["title"], layout="wide")
    st.title(config["app"]["title"])
    catalog = catalog_from_config(config)
    tab_match, tab_series, tab_one, tab_many = st.tabs([
        "Один матч",
        "Много матчей",
        "Один турнир",
        "Много турниров",
    ])
    with tab_match:
        render_match_tab(config, catalog, multi=False)
    with tab_series:
        render_match_tab(config, catalog, multi=True)
    with tab_one:
        render_tournament_tab(config, catalog, multi=False)
    with tab_many:
        render_tournament_tab(config, catalog, multi=True)


def render_match_tab(config, catalog, multi):
    prefix = "series" if multi else "single"
    states = list(weather_by_id(config).values())
    labels = {item["label"]: item for item in states}
    left, right = st.columns(2)
    with left:
        team1 = _pick_team(catalog, "Команда 1", prefix + "-t1", default_rank=1, help_text=HELP["team"])
        rating1 = st.number_input(
            "Рейтинг команды 1",
            min_value=0.0,
            value=float(team1.start_rating),
            step=1.0,
            key=prefix + "-r1-" + str(int(team1.team_id)),
            help=HELP["rating"],
        )
        st.caption(f"Opta: {team1.opta_rating:.1f}")
        squad1 = st.slider("Состав команды 1, %", 0, 100, 100, key=prefix + "-s1", help=HELP["squad"])
    with right:
        team2 = _pick_team(catalog, "Команда 2", prefix + "-t2", default_rank=6, help_text=HELP["team"])
        rating2 = st.number_input(
            "Рейтинг команды 2",
            min_value=0.0,
            value=float(team2.start_rating),
            step=1.0,
            key=prefix + "-r2-" + str(int(team2.team_id)),
            help=HELP["rating"],
        )
        st.caption(f"Opta: {team2.opta_rating:.1f}")
        squad2 = st.slider("Состав команды 2, %", 0, 100, 100, key=prefix + "-s2", help=HELP["squad"])

    home_code = st.radio(
        "Поле",
        ["neutral", "team1", "team2"],
        format_func=lambda code: {
            "neutral": "Нейтральное поле",
            "team1": f"Хозяева: {team1.team_name}",
            "team2": f"Хозяева: {team2.team_name}",
        }[code],
        horizontal=True,
        key=prefix + "-home",
        help=HELP["venue"],
    )
    weather_label = st.selectbox("Погода", list(labels), key=prefix + "-weather", help=HELP["weather"])
    described = describe_match(
        config, rating1, rating2, squad1, squad2,
        None if home_code == "neutral" else home_code,
        labels[weather_label],
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("mu", f"{described['mu']:.2f}", help=HELP["mu"])
    m2.metric("sigma", f"{described['sigma']:.2f}", help=HELP["sigma"])
    m3.metric(
        "Шансы по формуле",
        f"{described['p_win']:.1%} / {described['p_draw']:.1%} / {described['p_loss']:.1%}",
        help=HELP["formula"],
    )

    n_default = int(config["match"]["default_simulations"])
    n_sims = n_default
    if multi:
        n_sims = st.number_input(
            "Число симуляций", min_value=1, max_value=20000, value=n_default,
            key=prefix + "-n", help=HELP["n_sims"],
        )

    button = "Симулировать матчи" if multi else "Симулировать матч"
    button_help = HELP["simulate_matches"] if multi else HELP["simulate_match"]
    if _go_button(button, prefix + "-go", button_help):
        if int(team1.team_id) == int(team2.team_id):
            st.error("Выберите две разные команды.")
        elif multi:
            update = _progress_widgets()
            series = run_match_series(
                config, rating1, rating2, squad1, squad2,
                None if home_code == "neutral" else home_code, labels[weather_label], int(n_sims), update,
            )
            st.session_state[prefix + "-result"] = {
                "series": series,
                "team1": team1.team_name,
                "team2": team2.team_name,
            }
        else:
            played = play_match(
                config, rating1, rating2, squad1, squad2,
                None if home_code == "neutral" else home_code, labels[weather_label],
            )
            st.session_state[prefix + "-result"] = {"played": played, "team1": team1.team_name, "team2": team2.team_name}

    result = st.session_state.get(prefix + "-result")
    if not result:
        return
    if multi:
        series = result["series"]
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Победа {result['team1']}", f"{series['p_win']:.1%}", help=HELP["p_team"])
        c2.metric("Ничья", f"{series['p_draw']:.1%}", help=HELP["p_draw"])
        c3.metric(f"Победа {result['team2']}", f"{series['p_loss']:.1%}", help=HELP["p_team"])
        st.subheader("График разницы мячей", help=HELP["goal_chart"])
        st.plotly_chart(
            goal_diff_chart(series["diffs"], result["team1"], result["team2"]),
            use_container_width=True,
        )
    else:
        played = result["played"]
        st.header(f"{result['team1']} {played['score1']}:{played['score2']} {result['team2']}", help=HELP["score"])
        c1, c2, c3 = st.columns(3)
        c1.metric("mu", f"{played['mu']:.2f}", help=HELP["mu"])
        c2.metric("sigma", f"{played['sigma']:.2f}", help=HELP["sigma"])
        c3.metric("База голов", str(played["total"]), help=HELP["total"])
        d1, d2, d3 = st.columns(3)
        d1.metric(f"P({result['team1']})", f"{played['p_win']:.1%}", help=HELP["p_formula"])
        d2.metric("P(ничья)", f"{played['p_draw']:.1%}", help=HELP["p_formula"])
        d3.metric(f"P({result['team2']})", f"{played['p_loss']:.1%}", help=HELP["p_formula"])


def render_tournament_tab(config, catalog, multi):
    prefix = "many-tourn" if multi else "one-tourn"
    presets = {item["label"]: item for item in config["presets"]}
    preset_label = st.selectbox("Набор команд", list(presets), key=prefix + "-preset", help=HELP["preset"])
    preset = presets[preset_label]
    frame = _tournament_frame(catalog, preset, prefix)
    if frame is None or frame.empty:
        st.info("Выберите хотя бы две команды.")
        return

    view = frame[["team_name", "opta_rating", "start_rating"]].copy()
    view.columns = ["Команда", "Opta", "Рейтинг в модели"]
    edited = st.data_editor(
        view,
        disabled=["Команда", "Opta"],
        hide_index=True,
        num_rows="fixed",
        key=prefix + "-editor-" + str(tuple(int(item) for item in frame["team_id"])),
        column_config={
            "Команда": st.column_config.TextColumn(help=HELP["club_name"]),
            "Рейтинг в модели": st.column_config.NumberColumn(
                min_value=0.0, step=1.0, format="%.2f", help=HELP["model_rating"],
            ),
            "Opta": st.column_config.NumberColumn(format="%.1f", disabled=True, help=HELP["opta"]),
        },
    )
    teams_frame = frame.copy()
    teams_frame["start_rating"] = [float(value) for value in edited["Рейтинг в модели"]]

    mode, params = _format_controls(prefix)
    weather_on = st.checkbox("Случайная погода в каждом матче", key=prefix + "-weather", help=HELP["tour_weather"])
    fatigue_on = st.checkbox("Усталость состава", key=prefix + "-fatigue", help=HELP["fatigue"])
    n_sims = int(config["match"]["default_simulations"])
    if multi:
        n_sims = int(st.number_input(
            "Число симуляций", min_value=1, max_value=20000,
            value=n_sims, key=prefix + "-n", help=HELP["n_sims"],
        ))
        st.caption("Тысяча двукруговых турниров на 32 команды занимает около минуты.")

    button = "Симулировать турниры" if multi else "Симулировать турнир"
    button_help = HELP["simulate_tournaments"] if multi else HELP["simulate_tournament"]
    if _go_button(button, prefix + "-go", button_help):
        teams = teams_dict_from_frame(teams_frame)
        try:
            if multi:
                update = _progress_widgets()
                places = run_tournament_series(
                    teams, config, mode, params, weather_on, fatigue_on, n_sims, update,
                )
                st.session_state[prefix + "-result"] = {"places": places}
            else:
                one = run_tournament(teams, config, mode, params, weather_on, fatigue_on)
                one["weather_on"] = weather_on
                one["fatigue_on"] = fatigue_on
                st.session_state[prefix + "-result"] = one
        except ValueError as error:
            st.error(str(error))

    result = st.session_state.get(prefix + "-result")
    if not result:
        return
    if multi:
        places = result["places"]
        st.subheader("Тепловая карта мест", help=HELP["heatmap"])
        st.plotly_chart(place_heatmap(places), width="content")
        justice = justice_index(places)
        st.metric("Индекс справедливости", f"{justice:.1%}", help=HELP["justice"])
        for favorite in favorite_win_probability(places):
            st.metric(
                f"Первое место: {favorite['team_name']}",
                f"{favorite['probability']:.1%}",
                help=HELP["favorite"] + f" Рейтинг этой команды: {favorite['started_rating']:.0f}.",
            )
        return

    protocol = match_rows(result["log"], result["mode"])
    st.subheader("Матчи", help=HELP["matches"])
    st.dataframe(
        protocol,
        hide_index=True,
        width="stretch",
        height=min(520, 48 + 36 * max(len(protocol), 1)),
        column_config={
            "Счёт 1": st.column_config.NumberColumn(format="%d", help="Голы первой команды в этой строке."),
            "Счёт 2": st.column_config.NumberColumn(format="%d", help="Голы второй команды в этой строке."),
            "Тур": st.column_config.NumberColumn(help="Номер тура. В плей-офф 1 — это первый раунд сетки."),
            "Готовность 1": st.column_config.TextColumn(help="Состав первой команды в этом матче. Без усталости это 100%."),
            "Готовность 2": st.column_config.TextColumn(help="Состав второй команды в этом матче. Без усталости это 100%."),
            "Погода": st.column_config.TextColumn(help="Погода этого матча. Прочерк — фактор выключен."),
            "Серия пенальти": st.column_config.TextColumn(help="Да, если ничья в плей-офф решена серией. В круге и швейцарке ничья остаётся ничьей."),
        },
    )
    st.subheader("Таблица", help=HELP["table"])
    st.dataframe(standings_frame(result), hide_index=True, use_container_width=True)


def _tournament_frame(catalog, preset, prefix):
    if preset["kind"] != "custom":
        return preset_frame(catalog, preset)
    query = st.text_input(
        "Поиск клуба", key=prefix + "-search", placeholder="Начните вводить название", help=HELP["search"],
    )
    selected = st.session_state.get(prefix + "-selected", [])
    pool = catalog[catalog["team_id"].isin(selected)]
    if query.strip():
        mask = catalog["team_name"].str.contains(query.strip(), case=False, na=False)
        pool = catalog[mask | catalog["team_id"].isin(selected)]
    pool = pool.sort_values("opta_rank").head(400)
    options = pool["team_id"].tolist()
    labels = {int(row.team_id): row.team_name for row in pool.itertuples(index=False)}
    chosen = st.multiselect(
        "Команды",
        options=options,
        default=[item for item in selected if item in labels],
        format_func=lambda team_id: labels.get(int(team_id), str(team_id)),
        key=prefix + "-pick",
        help=HELP["custom_teams"],
    )
    st.session_state[prefix + "-selected"] = [int(item) for item in chosen]
    if not chosen:
        return catalog.iloc[0:0]
    return catalog[catalog["team_id"].isin(chosen)].sort_values("opta_rank")


def _format_controls(prefix):
    mode_labels = {
        "На вылет": "playoff",
        "Круг": "round_robin",
        "Группа и плей-офф": "combine",
        "Швейцарка": "swiss",
    }
    label = st.selectbox("Формат", list(mode_labels), key=prefix + "-format", help=HELP["format"])
    mode = mode_labels[label]
    params = {"cycles": 1, "rounds": 6, "groups": 4, "promote": 2, "seed": "half"}
    if mode == "playoff":
        params["seed"] = _seed_control(prefix)
    elif mode == "round_robin":
        params["cycles"] = int(st.number_input(
            "Число кругов", min_value=1, max_value=4, value=2, key=prefix + "-cycles", help=HELP["cycles"],
        ))
    elif mode == "swiss":
        params["rounds"] = int(st.number_input(
            "Число туров", min_value=1, max_value=30, value=6, key=prefix + "-rounds", help=HELP["rounds"],
        ))
    elif mode == "combine":
        params["groups"] = int(st.number_input(
            "Число групп", min_value=1, max_value=16, value=4, key=prefix + "-groups", help=HELP["groups"],
        ))
        params["promote"] = int(st.number_input(
            "Сколько команд выходит из группы", min_value=1, max_value=8, value=2,
            key=prefix + "-promote", help=HELP["promote"],
        ))
        params["cycles"] = int(st.number_input(
            "Кругов в группе", min_value=1, max_value=4, value=1, key=prefix + "-gcycles", help=HELP["group_cycles"],
        ))
        params["seed"] = _seed_control(prefix)
    return mode, params


def _seed_control(prefix):
    choice = st.radio(
        "Посев плей-офф", ["По рейтингу", "Случайный"],
        horizontal=True, key=prefix + "-seed", help=HELP["seed"],
    )
    return "half" if choice == "По рейтингу" else "random"


def _pick_team(catalog, label, key, default_rank, help_text):
    ids = [int(item) for item in catalog["team_id"].tolist()]
    names = dict(zip(ids, catalog["team_name"].tolist()))
    target_rows = catalog.loc[catalog["opta_rank"] == default_rank, "team_id"]
    target = int(target_rows.iloc[0]) if len(target_rows) else ids[0]
    team_id = st.selectbox(
        label, ids, index=ids.index(target),
        format_func=lambda item: names[int(item)], key=key, help=help_text,
    )
    return catalog.loc[catalog["team_id"] == int(team_id)].iloc[0]


def _go_button(label, key, help_text):
    action, hint = st.columns([2, 5])
    with action:
        pressed = st.button(label, type="primary", key=key)
    with hint:
        with st.popover("?", type="tertiary"):
            st.write(help_text)
    return pressed


def _progress_widgets():
    label = st.empty()
    bar = st.progress(0)

    def update(done, total):
        if not should_report(done, total):
            return
        bar.progress(done / total)
        label.write(f"{done} из {total} · {done / total:.0%}")

    return update


if __name__ == "__main__":
    main()
