import sys
import os
import tempfile
from pathlib import Path
from datetime import date

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent))

from config import (INITIAL_CAPITAL, DEPOSITS, ACCOUNT_COLORS, DATA_DIR,
                    CENT_DIVISOR, ACCOUNT_START_DATES, ACCOUNT_LABELS)
from src.parser import load_all_accounts, parse_mt4_html
from src.metrics import calc_metrics, calc_daily_pl, calc_account_summary
from src.charts import (
    plot_equity_curve, plot_daily_pl, plot_pl_distribution,
    plot_drawdown, plot_monthly_heatmap, plot_win_loss_pie,
)

UPLOAD_PASSWORD = "xauadmin"

st.set_page_config(
    page_title="XAUUSD Trading Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    html, body, [class*="css"]  { font-family: 'Calibri','Segoe UI',Arial,sans-serif; }
    * { font-family: 'Calibri','Segoe UI',Arial,sans-serif; }
    
    .kpi-card {
        background: #1a1a2e; border-radius: 10px; padding: 16px 20px;
        border: 1px solid #2a2a4a; height: 100%;
    }
    .kpi-label {
        font-size: 0.72rem; color: #888; text-transform: uppercase;
        letter-spacing: 0.5px; font-weight: 400;
    }
    .kpi-value {
        font-size: 1.5rem; font-weight: 700; margin-top: 4px;
    }
    .kpi-positive { color: #00cc96; }
    .kpi-negative { color: #ef553b; }
    .kpi-neutral  { color: #e0e0e0; }
    .stApp { background: #0f0f1a; }
    h1, h2, h3, h4, p, span, div, label, li {
        font-family: 'Calibri','Segoe UI',Arial,sans-serif !important;
        color: #e0e0e0 !important;
    }
    .stDataFrame { border: 1px solid #2a2a4a; border-radius: 8px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; overflow-x: auto; }
    .stTabs [data-baseweb="tab"] {
        background: #1a1a2e; border-radius: 8px 8px 0 0; padding: 8px 16px;
        white-space: nowrap;
    }
    .info-line {
        font-size: 0.8rem; color: #666; text-align: center;
        margin-top: 4px; letter-spacing: 0.3px;
    }

    @media (max-width: 768px) {
        .kpi-value { font-size: 1.1rem; }
        .kpi-card { padding: 10px 12px; }
        .stTabs [data-baseweb="tab"] { padding: 6px 10px; font-size: 0.85rem; }
        .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    }
    @media (max-width: 480px) {
        .kpi-value { font-size: 0.95rem; }
        .kpi-card { padding: 8px 10px; }
        .kpi-label { font-size: 0.65rem; }
        h1 { font-size: 1.3rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ── Title ──
acc_type_label = "美分帳戶" if CENT_DIVISOR > 1 else "標準帳戶"

deposit_info_parts = [f"初始本金 ${INITIAL_CAPITAL:,.0f}"]
for dep in DEPOSITS:
    deposit_info_parts.append(
        f"額外入金 ${dep['amount']:,.0f} ({dep['date'].strftime('%m/%d')})"
    )
deposit_info = " ｜ ".join(deposit_info_parts)

st.title("📊 XAUUSD 交易 Dashboard")
st.markdown(
    f'<div class="info-line">{deposit_info} ｜ 帳戶類型：{acc_type_label}</div>',
    unsafe_allow_html=True,
)

# ── Load data (files or uploaded) ──
@st.cache_data
def load_trades(data_dir, divisor):
    return load_all_accounts(data_dir, cent_divisor=divisor)

# Check for uploaded data in session state
if "uploaded_trades" in st.session_state:
    trades = st.session_state.uploaded_trades
else:
    trades = load_trades(DATA_DIR, CENT_DIVISOR)

if trades.empty:
    # Try uploaded files fallback
    if "uploaded_raw" in st.session_state and st.session_state.uploaded_raw:
        records = []
        for fname, content in st.session_state.uploaded_raw.items():
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
                f.write(content)
                tmppath = f.name
            df = parse_mt4_html(tmppath, account_label=fname.replace(".html", ""),
                                cent_divisor=CENT_DIVISOR)
            os.unlink(tmppath)
            if df is not None and len(df) > 0:
                records.append(df)
        if records:
            trades = pd.concat(records, ignore_index=True)
            trades = trades.sort_values("CloseTime").reset_index(drop=True)
            st.session_state.uploaded_trades = trades

if trades.empty:
    st.warning(f"`{DATA_DIR}/` 中找不到 HTML 檔案。請放入 MT4 匯出既報表。")
    st.stop()

# ── Filter by start dates ──
if "Account" in trades.columns and ACCOUNT_START_DATES:
    before = len(trades)
    mask = pd.Series(True, index=trades.index)
    for acc, start_date in ACCOUNT_START_DATES.items():
        mask &= ~((trades["Account"] == acc) & (trades["CloseTime"] < pd.Timestamp(start_date)))
    trades = trades[mask].copy()

# ── Account labels ──
def acc_label(acc):
    return ACCOUNT_LABELS.get(acc, str(acc))

if "Account" in trades.columns:
    trades["AccountLabel"] = trades["Account"].apply(acc_label)

# ── Metrics ──
deposits = [{"date": pd.Timestamp(d["date"]), "amount": d["amount"]} for d in DEPOSITS]
metrics = calc_metrics(trades, deposits, INITIAL_CAPITAL)
daily_pl = calc_daily_pl(trades)
account_summary = calc_account_summary(
    trades,
    account_col="AccountLabel" if "AccountLabel" in trades.columns else "Account",
)

days_running = (date.today() - date(2026, 3, 31)).days

# ════════════════════════════════════════
# KPI ROW 1
# ════════════════════════════════════════
st.subheader("📈 整體表現")

kpi1_data = [
    ("總盈虧", f"${metrics['total_pl']:+,.2f}", "pos" if metrics["total_pl"] >= 0 else "neg"),
    ("回報率", f"{metrics['return_pct']:+.2f}%", "pos" if metrics["return_pct"] >= 0 else "neg"),
    ("勝率", f"{metrics['win_rate']*100:.1f}%", "pos"),
    ("獲利因子", f"{metrics['profit_factor']:.2f}", "pos" if metrics["profit_factor"] >= 1 else "neg"),
    ("夏普比率", f"{metrics['sharpe_ratio']:.2f}", "pos" if metrics["sharpe_ratio"] >= 1 else "neg"),
    ("最大回撤", f"-{metrics['max_drawdown_pct']:.2f}%", "neg"),
]

cols1 = st.columns(6)
for col, (label, value, cls) in zip(cols1, kpi1_data):
    with col:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value kpi-{cls}">{value}</div></div>',
            unsafe_allow_html=True,
        )

# ════════════════════════════════════════
# KPI ROW 2
# ════════════════════════════════════════
kpi2_data = [
    ("交易次數", f"{metrics['total_trades']}", "neutral"),
    ("平均獲利", f"${metrics['avg_win']:+,.2f}", "pos" if metrics["avg_win"] >= 0 else "neg"),
    ("平均虧損", f"${metrics['avg_loss']:+,.2f}", "neg" if metrics["avg_loss"] < 0 else "pos"),
    ("盈虧比", f"{metrics['rr_ratio']:.2f}", "pos" if metrics["rr_ratio"] >= 1 else "neg"),
    ("已運行日數", f"{days_running} 天", "neutral"),
    ("最終權益", f"${metrics['final_equity']:+,.2f}", "pos"),
]

cols2 = st.columns(6)
for col, (label, value, cls) in zip(cols2, kpi2_data):
    with col:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value kpi-{cls}">{value}</div></div>',
            unsafe_allow_html=True,
        )

st.divider()

# ════════════════════════════════════════
# TABS
# ════════════════════════════════════════
tab1, tab2, tab3 = st.tabs(["📈 總覽", "👤 帳戶", "📋 交易紀錄"])

# ────────────────────────────────────────
# TAB 1 – 總覽
# ────────────────────────────────────────
with tab1:
    show_right = st.checkbox("顯示詳細圖表", value=True, key="show_right")

    col_l, col_r = st.columns([3, 2]) if show_right else (st.columns([1])[0], None)

    with col_l:
        st.plotly_chart(
            plot_equity_curve(metrics["equity_df"], metrics),
            use_container_width=True,
        )
        st.plotly_chart(plot_daily_pl(daily_pl), use_container_width=True)

    if show_right and col_r:
        with col_r:
            st.plotly_chart(plot_win_loss_pie(trades), use_container_width=True)
            st.plotly_chart(plot_pl_distribution(trades), use_container_width=True)

    st.plotly_chart(plot_drawdown(metrics["equity_df"]), use_container_width=True)

# ────────────────────────────────────────
# TAB 2 – 帳戶
# ────────────────────────────────────────
with tab2:
    if "Account" in trades.columns:
        accounts = sorted(trades["Account"].unique())
        if len(accounts) == 1:
            acc = accounts[0]
            at = trades[trades["Account"] == acc]
            am = calc_metrics(at, [], 0)
            acols = st.columns(4)
            for c, (l, v, p) in zip(acols, [
                ("交易次數", f"{am['total_trades']}", True),
                ("盈虧", f"${am['total_pl']:+,.2f}", am["total_pl"] >= 0),
                ("勝率", f"{am['win_rate']*100:.1f}%", True),
                ("獲利因子", f"{am['profit_factor']:.2f}", am["profit_factor"] >= 1),
            ]):
                with c:
                    cl = "kpi-positive" if p else "kpi-negative"
                    st.markdown(
                        f'<div class="kpi-card"><div class="kpi-label">{l}</div>'
                        f'<div class="kpi-value {cl}">{v}</div></div>',
                        unsafe_allow_html=True,
                    )
            ac1, ac2 = st.columns(2)
            with ac1:
                ad = calc_daily_pl(at)
                if not ad.empty:
                    st.plotly_chart(plot_daily_pl(ad), use_container_width=True)
            with ac2:
                st.plotly_chart(plot_pl_distribution(at), use_container_width=True)
        else:
            acc_tabs = st.tabs([acc_label(a) for a in accounts])
            for i, (acc_tab, acc) in enumerate(zip(acc_tabs, accounts)):
                with acc_tab:
                    at = trades[trades["Account"] == acc]
                    am = calc_metrics(at, [], 0)
                    acols = st.columns(4)
                    for c, (l, v, p) in zip(acols, [
                        ("交易次數", f"{am['total_trades']}", True),
                        ("盈虧", f"${am['total_pl']:+,.2f}", am["total_pl"] >= 0),
                        ("勝率", f"{am['win_rate']*100:.1f}%", True),
                        ("獲利因子", f"{am['profit_factor']:.2f}", am["profit_factor"] >= 1),
                    ]):
                        with c:
                            cl = "kpi-positive" if p else "kpi-negative"
                            st.markdown(
                                f'<div class="kpi-card"><div class="kpi-label">{l}</div>'
                                f'<div class="kpi-value {cl}">{v}</div></div>',
                                unsafe_allow_html=True,
                            )
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        ad = calc_daily_pl(at)
                        if not ad.empty:
                            st.plotly_chart(plot_daily_pl(ad), use_container_width=True)
                    with ac2:
                        st.plotly_chart(plot_pl_distribution(at), use_container_width=True)

            st.subheader("帳戶比較")
            if not account_summary.empty:
                rename = {
                    "Account": "帳戶", "TradeCount": "交易次數", "TotalPL": "總盈虧",
                    "WinCount": "獲利", "LossCount": "虧損",
                    "WinRate": "勝率(%)", "ProfitFactor": "獲利因子",
                    "GrossProfit": "毛利", "GrossLoss": "毛損",
                    "AvgWin": "平均獲利", "AvgLoss": "平均虧損",
                }
                st.dataframe(
                    account_summary.rename(columns=rename),
                    use_container_width=True,
                    column_config={
                        "總盈虧": st.column_config.NumberColumn(format="$%.2f"),
                        "毛利": st.column_config.NumberColumn(format="$%.2f"),
                        "毛損": st.column_config.NumberColumn(format="$%.2f"),
                        "平均獲利": st.column_config.NumberColumn(format="$%.2f"),
                        "平均虧損": st.column_config.NumberColumn(format="$%.2f"),
                    },
                )
    else:
        st.info("交易數據中沒有帳戶資訊。")

# ────────────────────────────────────────
# TAB 3 – 交易紀錄
# ────────────────────────────────────────
with tab3:
    with st.expander("🔍 篩選條件", expanded=False):
        c_filt_cols = st.columns([1, 1, 1])
        with c_filt_cols[0]:
            dr = st.date_input(
                "日期範圍",
                value=(trades["CloseTime"].min().date(), trades["CloseTime"].max().date()),
                label_visibility="collapsed",
            )
        with c_filt_cols[1]:
            if "Account" in trades.columns:
                acc_opts = sorted(trades["Account"].unique())
                sa = st.multiselect(
                    "帳戶", options=acc_opts, default=acc_opts,
                    format_func=lambda a: acc_label(a), label_visibility="collapsed",
                )
            else:
                sa = None
        with c_filt_cols[2]:
            m1, m2 = st.slider(
                "盈虧範圍",
                min_value=float(trades["Profit"].min()),
                max_value=float(trades["Profit"].max()),
                value=(float(trades["Profit"].min()), float(trades["Profit"].max())),
                label_visibility="collapsed",
            )

    filtered = trades.copy()
    if len(dr) == 2:
        s, e = dr
        filtered = filtered[
            (filtered["CloseTime"].dt.date >= s) & (filtered["CloseTime"].dt.date <= e)
        ]
    if sa and "Account" in filtered.columns:
        filtered = filtered[filtered["Account"].isin(sa)]
    filtered = filtered[(filtered["Profit"] >= m1) & (filtered["Profit"] <= m2)]

    st.markdown(f"**共 {len(filtered)} 筆交易**")

    dc = ["CloseTime", "Type", "Size", "Item", "ClosePrice", "Profit"]
    if "Account" in filtered.columns:
        dc.insert(1, "AccountLabel")

    col_config = {
        "CloseTime": st.column_config.DatetimeColumn("平倉時間"),
        "AccountLabel": st.column_config.TextColumn("帳戶"),
        "Type": st.column_config.TextColumn("類型"),
        "Size": st.column_config.NumberColumn("手數", format="%.2f"),
        "Item": st.column_config.TextColumn("品種"),
        "ClosePrice": st.column_config.NumberColumn("平倉價", format="%.2f"),
        "Profit": st.column_config.NumberColumn("盈虧", format="$%.2f"),
    }

    st.dataframe(
        filtered[dc].sort_values("CloseTime", ascending=False).reset_index(drop=True),
        use_container_width=True,
        height=min(600, 40 * len(filtered) + 40),
        column_config={k: col_config[k] for k in dc if k in col_config},
        hide_index=True,
    )

# ── 管理員：更新數據 ──
with st.expander("🔐 管理員 — 更新交易數據"):
    pw = st.text_input("密碼", type="password", label_visibility="collapsed")
    if pw == UPLOAD_PASSWORD:
        uploaded = st.file_uploader(
            "上傳 MT4 HTML 報表（可選多個）",
            type=["html", "htm"],
            accept_multiple_files=True,
        )
        if uploaded:
            raw_data = {}
            for f in uploaded:
                raw_data[f.name] = f.read()
            st.session_state.uploaded_raw = raw_data
            if "uploaded_trades" in st.session_state:
                del st.session_state.uploaded_trades
            st.cache_data.clear()
            st.success(f"已上傳 {len(uploaded)} 個檔案，正在重新載入…")
            st.rerun()
    elif pw:
        st.error("密碼錯誤")

# ── Footer ──
st.divider()
acct_count = trades['Account'].nunique() if 'Account' in trades.columns else 'N/A'
st.caption(
    f"數據來源：`{DATA_DIR}/`　｜　"
    f"{len(trades)} 筆交易　｜　{acct_count} 個帳戶　｜　"
    f"{acc_type_label}"
)
