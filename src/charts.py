import plotly.graph_objects as go
import pandas as pd
import numpy as np

_THEME = dict(
    paper_bgcolor="#0f0f1a",
    plot_bgcolor="#0f0f1a",
    font=dict(color="#c0c0c0", size=11, family="Calibri, Segoe UI, Arial"),
    xaxis=dict(
        gridcolor="#1e1e30", griddash="dot", linecolor="#2a2a40", zerolinecolor="#2a2a40"
    ),
    yaxis=dict(
        gridcolor="#1e1e30", griddash="dot", linecolor="#2a2a40", zerolinecolor="#2a2a40"
    ),
)

_PAPER_MARGINS = dict(l=8, r=8, t=48, b=8)

_TITLE_FONT = dict(size=18, color="#e0e0e0", family="Calibri, Segoe UI, Arial")


def _apply_theme(fig):
    fig.update_layout(**_THEME, margin=_PAPER_MARGINS)
    return fig


def plot_equity_curve(equity_df, metrics):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=equity_df["Date"],
            y=equity_df["Equity"],
            mode="lines",
            name="權益曲線",
            line=dict(color="#636efa", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(99,110,250,0.08)",
            hovertemplate="%{x|%Y-%m-%d}<br><b>$%{y:,.2f}</b><extra></extra>",
        )
    )

    total_dep = metrics["total_deposits"]
    fig.add_hline(
        y=total_dep,
        line_dash="dash",
        line_color="rgba(150,150,150,0.4)",
        line_width=1,
        annotation_text=f"總入金 ${total_dep:,.0f}",
        annotation_position="bottom right",
        annotation_font=dict(size=10, color="#888"),
    )

    dd_end = equity_df.loc[
        (equity_df["Equity"] - equity_df["Equity"].cummax()).idxmin()
    ]
    fig.add_trace(
        go.Scatter(
            x=[dd_end["Date"]],
            y=[dd_end["Equity"]],
            mode="markers",
            marker=dict(size=12, color="#ef553b", symbol="x", line=dict(width=1, color="white")),
            name=f"最大回撤 -{metrics['max_drawdown_pct']:.1f}%",
            hovertemplate=(
                "<b>最大回撤</b><br>"
                "%{x|%Y-%m-%d}<br>"
                "-$%{customdata[0]:,.0f} (-%{customdata[1]:.1f}%)<extra></extra>"
            ),
            customdata=[[metrics["max_drawdown_amount"], metrics["max_drawdown_pct"]]],
        )
    )

    fig.update_layout(
        title=dict(text="權益曲線", font=_TITLE_FONT),
        hovermode="x unified",
        height=380,
        yaxis=dict(tickprefix="$", range=[equity_df["Equity"].min() * 0.95, equity_df["Equity"].max() * 1.05]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
    )

    fig.update_xaxes(rangeslider=dict(visible=False))

    return _apply_theme(fig)


def plot_daily_pl(daily_df):
    max_abs = max(abs(daily_df["Profit"].min()), abs(daily_df["Profit"].max()))

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=daily_df["Date"],
            y=daily_df["Profit"],
            marker_color=["#00cc96" if v >= 0 else "#ef553b" for v in daily_df["Profit"]],
            marker_line=dict(width=0.3, color="#1a1a2e"),
            opacity=0.85,
            name="每日損益",
            hovertemplate="%{x|%Y-%m-%d}<br><b>$%{y:+,.2f}</b><extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=daily_df["Date"],
            y=daily_df["Cumulative"],
            mode="lines+markers",
            name="累計",
            line=dict(color="#636efa", width=2),
            marker=dict(size=4, color="#636efa"),
            yaxis="y2",
            hovertemplate="累計: $%{y:+,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text="每日損益", font=_TITLE_FONT),
        hovermode="x unified",
        height=340,
        yaxis=dict(
            tickprefix="$",
            range=[-max_abs * 1.2, max_abs * 1.2],
        ),
        yaxis2=dict(
            tickprefix="$",
            overlaying="y",
            side="right",
            showgrid=False,
            range=[daily_df["Cumulative"].min() * 1.1, daily_df["Cumulative"].max() * 1.1],
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        barmode="relative",
        barnorm=None,
        bargap=0.3,
    )

    return _apply_theme(fig)


def plot_pl_distribution(trades):
    wins = trades[trades["Profit"] > 0]["Profit"]
    losses = trades[trades["Profit"] < 0]["Profit"]
    all_profits = trades["Profit"]

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=all_profits,
            nbinsx=50,
            marker_color="#636efa",
            marker_line=dict(width=0.3, color="#1a1a2e"),
            opacity=0.75,
            name="盈虧分佈",
            hovertemplate="$%{x:,.2f}<br>次數: %{y}<extra></extra>",
        )
    )

    annotations = []
    if len(wins) > 0:
        avg_w = wins.mean()
        fig.add_vline(x=avg_w, line_dash="dash", line_color="#00cc96", line_width=1.5)
        annotations.append(dict(x=avg_w, y=1, xref="x", yref="paper",
                                text=f"平均獲利 ${avg_w:.2f}", showarrow=False,
                                font=dict(color="#00cc96", size=10),
                                yanchor="bottom", xanchor="left" if avg_w < 0 else "right"))

    if len(losses) > 0:
        avg_l = losses.mean()
        fig.add_vline(x=avg_l, line_dash="dash", line_color="#ef553b", line_width=1.5)
        annotations.append(dict(x=avg_l, y=1, xref="x", yref="paper",
                                text=f"平均虧損 ${avg_l:.2f}", showarrow=False,
                                font=dict(color="#ef553b", size=10),
                                yanchor="bottom", xanchor="right"))

    # Vertical line at zero
    fig.add_vline(x=0, line_color="rgba(255,255,255,0.15)", line_width=1)

    fig.update_layout(
        title=dict(text="盈虧分佈", font=_TITLE_FONT),
        hovermode="x",
        height=340,
        xaxis=dict(tickprefix="$"),
        yaxis=dict(title="交易次數"),
        bargap=0.08,
        annotations=annotations,
    )

    return _apply_theme(fig)


def plot_drawdown(equity_df):
    equity = equity_df["Equity"].values
    peak = np.maximum.accumulate(equity)
    dd_pct = (peak - equity) / peak * 100

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=equity_df["Date"],
            y=dd_pct,
            mode="lines",
            name="回撤",
            line=dict(color="#ef553b", width=2),
            fill="tozeroy",
            fillcolor="rgba(239,85,59,0.12)",
            hovertemplate="%{x|%Y-%m-%d}<br><b>- %{y:.2f}%</b><extra></extra>",
        )
    )

    max_dd = dd_pct.max()
    fig.add_hline(
        y=max_dd,
        line_dash="dash",
        line_color="rgba(239,85,59,0.3)",
        line_width=1,
        annotation_text=f"最大 -{max_dd:.2f}%",
        annotation_position="top right",
        annotation_font=dict(size=10, color="#ef553b"),
    )

    fig.update_layout(
        title=dict(text="資金回撤", font=_TITLE_FONT),
        hovermode="x unified",
        height=220,
        yaxis=dict(ticksuffix="%", range=[dd_pct.max() * 1.15, 0]),
        showlegend=False,
    )

    return _apply_theme(fig)


def plot_monthly_heatmap(trades):
    df = trades.dropna(subset=["CloseTime"]).copy()
    df["Year"] = df["CloseTime"].dt.year
    df["Month"] = df["CloseTime"].dt.month

    monthly = df.groupby(["Year", "Month"])["Profit"].sum().reset_index()

    years = sorted(monthly["Year"].unique())
    month_labels = ["一月", "二月", "三月", "四月", "五月", "六月",
                    "七月", "八月", "九月", "十月", "十一月", "十二月"]

    z = []
    for y in years:
        row = []
        for m in range(1, 13):
            val = monthly[(monthly["Year"] == y) & (monthly["Month"] == m)]
            row.append(val["Profit"].values[0] if len(val) > 0 else None)
        z.append(row)

    max_abs_val = max(abs(v) for row in z for v in row if v is not None) if any(
        v is not None for row in z for v in row) else 1

    colorscale = [
        [0, "#8b0000"],
        [0.25, "#ef553b"],
        [0.45, "#2a1a1a"],
        [0.5, "#1a1a2e"],
        [0.55, "#1a2a1a"],
        [0.75, "#00cc96"],
        [1, "#006644"],
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Heatmap(
            z=z,
            y=[str(y) for y in years],
            x=month_labels,
            colorscale=colorscale,
            zmid=0,
            zmin=-max_abs_val,
            zmax=max_abs_val,
            hovertemplate="%{y} %{x}<br><b>$%{z:+,.0f}</b><extra></extra>",
            showscale=True,
            colorbar=dict(title="$", tickprefix="$", len=0.7, thickness=12),
        )
    )

    fig.update_layout(
        title=dict(text="每月損益熱力圖", font=_TITLE_FONT),
        height=220,
        xaxis=dict(side="top", tickfont=dict(size=10)),
        yaxis=dict(tickfont=dict(size=10)),
    )

    return _apply_theme(fig)


def plot_win_loss_pie(trades):
    wins = (trades["Profit"] > 0).sum()
    losses = (trades["Profit"] < 0).sum()
    evens = (trades["Profit"] == 0).sum()

    labels, values, colors = [], [], []
    if wins > 0:
        labels.append(f"獲利 ({wins})")
        values.append(wins)
        colors.append("#00cc96")
    if losses > 0:
        labels.append(f"虧損 ({losses})")
        values.append(losses)
        colors.append("#ef553b")
    if evens > 0:
        labels.append(f"持平 ({evens})")
        values.append(evens)
        colors.append("#636efa")

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors, line=dict(color="#0f0f1a", width=2)),
            textinfo="label+percent",
            textfont=dict(size=12),
            hovertemplate="%{label}<br>次數: %{value}<extra></extra>",
            pull=[0.03] + [0] * (len(labels) - 1),
        )
    )

    fig.update_layout(
        title=dict(text="獲利／虧損分佈", font=_TITLE_FONT),
        height=300,
        showlegend=False,
    )

    return _apply_theme(fig)
