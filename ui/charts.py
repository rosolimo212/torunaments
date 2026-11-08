# coding: utf-8
"""Графики Plotly для вкладок матча и турнира."""

import plotly.graph_objects as go

from core.simulate import place_matrix


def format_goal_diff(value):
    value = int(value)
    if value > 0:
        return "+" + str(value)
    return str(value)


def goal_diff_chart(diffs, team1, team2):
    series = {}
    for value in diffs:
        key = int(value)
        series[key] = series.get(key, 0) + 1
    keys = sorted(series)
    total = len(diffs) or 1
    labels = [format_goal_diff(key) for key in keys]
    shares = [series[key] / total for key in keys]
    figure = go.Figure(go.Bar(
        x=labels,
        y=shares,
        marker_color="#1f6f6a",
        hovertemplate="разница %{x}<br>%{y:.1%}<extra></extra>",
    ))
    figure.update_layout(
        title=f"Разница мячей: {team1} минус {team2}",
        xaxis_title="Голы первой команды минус голы второй",
        yaxis_title="Доля симуляций",
        yaxis_tickformat=".0%",
        height=420,
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return figure


def place_heatmap(place_df):
    shares, _normalized = place_matrix(place_df)
    teams = [name for _rating, name in shares.index]
    places = [str(column) for column in shares.columns]
    values = shares.values
    annotate = len(teams) <= 16
    text = [[f"{cell:.0%}" for cell in row] for row in values] if annotate else None
    zmin = float(values.min())
    zmax = float(values.max())
    if zmax <= zmin:
        zmax = zmin + 1e-6
    figure = go.Figure(go.Heatmap(
        z=values,
        x=places,
        y=teams,
        text=text,
        texttemplate="%{text}" if annotate else None,
        colorscale="Teal",
        zmin=zmin,
        zmax=zmax,
        hovertemplate="место %{x}<br>%{y}<br>%{z:.1%}<extra></extra>",
        colorbar=dict(tickformat=".0%"),
    ))
    figure.update_layout(
        xaxis_title="Место",
        height=max(420, 26 * len(teams) + 120),
        margin=dict(l=10, r=10, t=30, b=40),
    )
    figure.update_yaxes(autorange="reversed")
    return figure
