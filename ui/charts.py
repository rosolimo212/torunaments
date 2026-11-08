# coding: utf-8
"""Графики Plotly для вкладок матча и турнира."""

import plotly.graph_objects as go

from core.simulate import place_matrix


def format_goal_diff(value):
    value = int(value)
    if value > 0:
        return "+" + str(value)
    return str(value)


WIN_COLOR = "#2a9d8f"
DRAW_COLOR = "#e9c46a"
LOSS_COLOR = "#e76f51"


def goal_diff_phrase(value, team1, team2):
    value = int(value)
    if value > 0:
        return f"Разница {value}: в пользу {team1}"
    if value < 0:
        return f"Разница {-value}: в пользу {team2}"
    return "Разница 0: ничья"


def goal_diff_chart(diffs, team1, team2):
    series = {}
    for value in diffs:
        key = int(value)
        series[key] = series.get(key, 0) + 1
    keys = sorted(series)
    total = len(diffs) or 1
    labels = [format_goal_diff(key) for key in keys]
    shares = [series[key] / total for key in keys]
    colors = []
    hovers = []
    for key in keys:
        if key > 0:
            colors.append(WIN_COLOR)
        elif key < 0:
            colors.append(LOSS_COLOR)
        else:
            colors.append(DRAW_COLOR)
        hovers.append(goal_diff_phrase(key, team1, team2))
    figure = go.Figure(go.Bar(
        x=labels,
        y=shares,
        marker_color=colors,
        customdata=hovers,
        hovertemplate="%{customdata}<br>доля %{y:.1%}<extra></extra>",
        showlegend=False,
    ))
    for name, color in (
        (f"Победа {team1}", WIN_COLOR),
        ("Ничья", DRAW_COLOR),
        (f"Победа {team2}", LOSS_COLOR),
    ):
        figure.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=12, color=color, symbol="square"),
            name=name,
            hoverinfo="skip",
            showlegend=True,
        ))
    figure.update_layout(
        title=f"Разница мячей: {team1} минус {team2}",
        xaxis_title="Голы первой команды минус голы второй",
        yaxis_title="Доля симуляций",
        yaxis_tickformat=".0%",
        height=460,
        margin=dict(l=40, r=20, t=80, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    figure.update_xaxes(categoryorder="array", categoryarray=labels)
    return figure


def place_heatmap(place_df):
    shares, _normalized = place_matrix(place_df)
    teams = [name for _rating, name in shares.index]
    places = [str(column) for column in shares.columns]
    values = shares.values
    n_rows = len(teams)
    n_cols = max(len(places), 1)
    annotate_all = n_rows <= 16
    place_at = {int(place): index for index, place in enumerate(places)}
    zmin = float(values.min())
    zmax = float(values.max())
    if zmax <= zmin:
        zmax = zmin + 1e-6
    midpoint = (zmin + zmax) / 2
    annotations = []
    for row_index, team in enumerate(teams):
        diagonal_col = place_at.get(row_index + 1)
        for column_index, cell in enumerate(values[row_index]):
            on_diagonal = column_index == diagonal_col
            if not on_diagonal and not annotate_all:
                continue
            dark = (zmax - zmin) > 1e-4 and float(cell) >= midpoint
            annotations.append(dict(
                # Номер места — это текст «1», «2», … Plotly читает его как число
                # и сдвигает подпись на клетку вправо. Поэтому координата — индекс.
                x=column_index,
                y=team,
                text=f"{float(cell):.0%}",
                showarrow=False,
                font=dict(
                    size=15 if on_diagonal else 12,
                    color="#f7fffd" if dark else "#10211f",
                    family="Arial Black, Arial" if on_diagonal else "Arial",
                ),
                xref="x",
                yref="y",
            ))
    cell = 54 if n_rows <= 12 else (36 if n_rows <= 20 else 26)
    # Правый и нижний запасы оставляют шкалу и подпись «Место» снаружи клеток,
    # иначе Plotly уменьшает поле графика и клетки перестают быть квадратными.
    left, right, top, bottom = 188, 100, 20, 84
    figure = go.Figure(go.Heatmap(
        z=values,
        x=places,
        y=teams,
        colorscale="Teal",
        zmin=zmin,
        zmax=zmax,
        hovertemplate="место %{x}<br>%{y}<br>%{z:.1%}<extra></extra>",
        colorbar=dict(tickformat=".0%", thickness=14, len=1, x=1.03),
        xgap=2,
        ygap=2,
    ))
    figure.update_layout(
        width=left + cell * n_cols + right,
        height=top + cell * n_rows + bottom,
        margin=dict(l=left, r=right, t=top, b=bottom),
        annotations=annotations,
        xaxis=dict(
            title="Место",
            type="category",
            range=[-0.5, n_cols - 0.5],
            tickfont=dict(size=12),
        ),
        yaxis=dict(
            type="category",
            range=[n_rows - 0.5, -0.5],
            tickfont=dict(size=12),
        ),
    )
    return figure
