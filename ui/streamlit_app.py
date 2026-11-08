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
        team1 = _pick_team(catalog, "Команда 1", prefix + "-t1", default_rank=1)
        rating1 = st.number_input(
            "Рейтинг команды 1",
            min_value=0.0,
            value=float(team1.start_rating),
            step=1.0,
            key=prefix + "-r1-" + str(int(team1.team_id)),
        )
        st.caption(f"Opta: {team1.opta_rating:.1f}")
        squad1 = st.slider("Состав команды 1, %", 0, 100, 100, key=prefix + "-s1")
    with right:
        team2 = _pick_team(catalog, "Команда 2", prefix + "-t2", default_rank=6)
        rating2 = st.number_input(
            "Рейтинг команды 2",
            min_value=0.0,
            value=float(team2.start_rating),
            step=1.0,
            key=prefix + "-r2-" + str(int(team2.team_id)),
        )
        st.caption(f"Opta: {team2.opta_rating:.1f}")
        squad2 = st.slider("Состав команды 2, %", 0, 100, 100, key=prefix + "-s2")

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
    )
    weather_label = st.selectbox("Погода", list(labels), key=prefix + "-weather")
    described = describe_match(
        config, rating1, rating2, squad1, squad2,
        None if home_code == "neutral" else home_code,
        labels[weather_label],
    )
    st.caption(
        f"mu = {described['mu']:.2f}, sigma = {described['sigma']:.2f}. "
        f"По формуле: победа {described['p_win']:.1%}, ничья {described['p_draw']:.1%}, "
        f"поражение {described['p_loss']:.1%}."
    )

    n_default = int(config["match"]["default_simulations"])
    n_sims = n_default
    if multi:
        n_sims = st.number_input("Число симуляций", min_value=1, max_value=20000, value=n_default, key=prefix + "-n")

    button = "Симулировать матчи" if multi else "Симулировать матч"
    if st.button(button, type="primary", key=prefix + "-go"):
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
        c1.metric(f"Победа {result['team1']}", f"{series['p_win']:.1%}")
        c2.metric("Ничья", f"{series['p_draw']:.1%}")
        c3.metric(f"Победа {result['team2']}", f"{series['p_loss']:.1%}")
        st.plotly_chart(
            goal_diff_chart(series["diffs"], result["team1"], result["team2"]),
            use_container_width=True,
        )
    else:
        played = result["played"]
        st.header(f"{result['team1']} {played['score1']}:{played['score2']} {result['team2']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("mu", f"{played['mu']:.2f}")
        c2.metric("sigma", f"{played['sigma']:.2f}")
        c3.metric("База голов", str(played["total"]))
        d1, d2, d3 = st.columns(3)
        d1.metric(f"P({result['team1']})", f"{played['p_win']:.1%}")
        d2.metric("P(ничья)", f"{played['p_draw']:.1%}")
        d3.metric(f"P({result['team2']})", f"{played['p_loss']:.1%}")


def render_tournament_tab(config, catalog, multi):
    prefix = "many-tourn" if multi else "one-tourn"
    presets = {item["label"]: item for item in config["presets"]}
    preset_label = st.selectbox("Набор команд", list(presets), key=prefix + "-preset")
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
            "Рейтинг в модели": st.column_config.NumberColumn(min_value=0.0, step=1.0, format="%.2f"),
            "Opta": st.column_config.NumberColumn(format="%.1f", disabled=True),
        },
    )
    teams_frame = frame.copy()
    teams_frame["start_rating"] = [float(value) for value in edited["Рейтинг в модели"]]

    mode, params = _format_controls(prefix)
    weather_on = st.checkbox("Случайная погода в каждом матче", key=prefix + "-weather")
    fatigue_on = st.checkbox("Усталость состава", key=prefix + "-fatigue")
    n_sims = int(config["match"]["default_simulations"])
    if multi:
        n_sims = int(st.number_input(
            "Число симуляций", min_value=1, max_value=20000,
            value=n_sims, key=prefix + "-n",
        ))
        st.caption("Тысяча двукруговых турниров на 32 команды занимает около минуты.")

    if st.button("Симулировать турнир" if not multi else "Симулировать турниры", type="primary", key=prefix + "-go"):
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
        st.plotly_chart(place_heatmap(places), use_container_width=True)
        justice = justice_index(places)
        st.metric("Индекс справедливости", f"{justice:.1%}")
        for favorite in favorite_win_probability(places):
            st.write(
                f"Первое место у {favorite['team_name']} "
                f"(рейтинг {favorite['started_rating']:.0f}): {favorite['probability']:.1%}"
            )
        return

    protocol = match_rows(result["log"], result["weather_on"], result["fatigue_on"])
    st.subheader("Матчи")
    if len(protocol) > 10:
        with st.expander(f"Показать матчи ({len(protocol)})"):
            st.dataframe(protocol, hide_index=True, use_container_width=True)
    else:
        st.dataframe(protocol, hide_index=True, use_container_width=True)
    st.subheader("Таблица")
    st.dataframe(standings_frame(result), hide_index=True, use_container_width=True)


def _tournament_frame(catalog, preset, prefix):
    if preset["kind"] != "custom":
        return preset_frame(catalog, preset)
    query = st.text_input("Поиск клуба", key=prefix + "-search", placeholder="Начните вводить название")
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
    label = st.selectbox("Формат", list(mode_labels), key=prefix + "-format")
    mode = mode_labels[label]
    params = {"cycles": 1, "rounds": 6, "groups": 4, "promote": 2, "seed": "half"}
    if mode == "playoff":
        params["seed"] = _seed_control(prefix)
    elif mode == "round_robin":
        params["cycles"] = int(st.number_input("Число кругов", min_value=1, max_value=4, value=2, key=prefix + "-cycles"))
    elif mode == "swiss":
        params["rounds"] = int(st.number_input("Число туров", min_value=1, max_value=30, value=6, key=prefix + "-rounds"))
    elif mode == "combine":
        params["groups"] = int(st.number_input("Число групп", min_value=1, max_value=16, value=4, key=prefix + "-groups"))
        params["promote"] = int(st.number_input("Сколько команд выходит из группы", min_value=1, max_value=8, value=2, key=prefix + "-promote"))
        params["cycles"] = int(st.number_input("Кругов в группе", min_value=1, max_value=4, value=1, key=prefix + "-gcycles"))
        params["seed"] = _seed_control(prefix)
    return mode, params


def _seed_control(prefix):
    choice = st.radio("Посев плей-офф", ["По рейтингу", "Случайный"], horizontal=True, key=prefix + "-seed")
    return "half" if choice == "По рейтингу" else "random"


def _pick_team(catalog, label, key, default_rank):
    ids = [int(item) for item in catalog["team_id"].tolist()]
    names = dict(zip(ids, catalog["team_name"].tolist()))
    target_rows = catalog.loc[catalog["opta_rank"] == default_rank, "team_id"]
    target = int(target_rows.iloc[0]) if len(target_rows) else ids[0]
    team_id = st.selectbox(label, ids, index=ids.index(target), format_func=lambda item: names[int(item)], key=key)
    return catalog.loc[catalog["team_id"] == int(team_id)].iloc[0]


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
