import pandas as pd
import numpy as np


def calc_metrics(trades, deposits_conf=None, initial_capital_conf=0):
    """Calculate performance metrics from trades and balance events."""
    if trades.empty:
        return {}

    total_trades = len(trades)
    winning_trades = trades[trades["Profit"] > 0]
    losing_trades = trades[trades["Profit"] < 0]

    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    win_rate = win_count / total_trades if total_trades > 0 else 0

    gross_profit = winning_trades["Profit"].sum() if win_count > 0 else 0
    gross_loss = losing_trades["Profit"].sum() if loss_count > 0 else 0
    profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else float("inf")

    total_pl = trades["Profit"].sum()
    total_swap = trades["Swap"].sum() if "Swap" in trades.columns else 0
    total_commission = trades["Commission"].sum() if "Commission" in trades.columns else 0

    avg_win = winning_trades["Profit"].mean() if win_count > 0 else 0
    avg_loss = losing_trades["Profit"].mean() if loss_count > 0 else 0
    rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

    largest_win = trades["Profit"].max()
    largest_loss = trades["Profit"].min()

    # Balance events
    bal_events = trades.attrs.get("balance_events")
    total_external_deposits, total_external_withdrawals = _calc_external_flows(bal_events)
    total_deposits = total_external_deposits + initial_capital_conf + \
                     (sum(d["amount"] for d in deposits_conf) if deposits_conf else 0)

    net_capital = total_deposits - total_external_withdrawals
    total_return = total_pl

    # Equity curve from all events
    equity_df = _build_equity_curve(trades, bal_events, initial_capital_conf, deposits_conf or [])

    final_equity = equity_df["Equity"].iloc[-1] if not equity_df.empty else 0
    return_pct = (final_equity - net_capital) / net_capital * 100 if net_capital > 0 else 0

    daily_returns = _calc_daily_returns(equity_df)
    sharpe = _calc_sharpe(daily_returns)
    max_dd_pct, max_dd_amount = _calc_max_drawdown(equity_df)

    recovery_factor = abs(total_pl / max_dd_amount) if max_dd_amount != 0 else float("inf")

    profitable_days = (daily_returns > 0).sum()
    total_days = len(daily_returns)
    daily_win_rate = profitable_days / total_days if total_days > 0 else 0

    return {
        "total_trades": total_trades,
        "win_count": win_count,
        "loss_count": loss_count,
        "even_count": total_trades - win_count - loss_count,
        "win_rate": win_rate,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "total_pl": total_pl,
        "total_swap": total_swap,
        "total_commission": total_commission,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "rr_ratio": rr_ratio,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": max_dd_pct,
        "max_drawdown_amount": max_dd_amount,
        "total_return": total_return,
        "return_pct": return_pct,
        "final_equity": final_equity,
        "total_deposits": total_deposits,
        "net_capital": net_capital,
        "external_deposits": total_external_deposits,
        "external_withdrawals": total_external_withdrawals,
        "recovery_factor": recovery_factor,
        "daily_win_rate": daily_win_rate,
        "equity_df": equity_df,
    }


def _calc_external_flows(bal_events):
    """Calculate total external deposits and withdrawals from balance events."""
    if bal_events is None or len(bal_events) == 0:
        return 0, 0

    deposits = 0
    withdrawals = 0
    for _, ev in bal_events.iterrows():
        typ = ev.get("Type", "")
        profit = ev.get("Profit", 0)
        comment = ev.get("Comment", "")

        if typ == "balance":
            if profit > 0:
                deposits += profit
            else:
                withdrawals += abs(profit)
        elif typ == "deposit":
            deposits += profit
        elif typ == "withdrawal":
            withdrawals += abs(profit)
        elif typ == "credit":
            deposits += profit
        elif typ == "bonus":
            deposits += profit

    return deposits, withdrawals


def _build_equity_curve(trades, bal_events, initial_capital, deposits_conf):
    """Build equity curve from all cash flows: trades, deposits, balance events."""
    events = []

    # Starting point
    first_time = trades["CloseTime"].min()
    events.append({"Time": first_time - pd.Timedelta(days=1), "Delta": initial_capital})

    # Config deposits
    for dep in deposits_conf:
        events.append({"Time": pd.Timestamp(dep["date"]), "Delta": dep["amount"]})

    # Balance events (external deposits/withdrawals parsed from files)
    if bal_events is not None:
        for _, ev in bal_events.iterrows():
            events.append({
                "Time": pd.Timestamp(ev["Time"]),
                "Delta": ev["Profit"],
            })

    # Trade profits
    for _, row in trades.iterrows():
        events.append({
            "Time": row["CloseTime"],
            "Delta": row["Profit"],
        })

    if not events:
        return pd.DataFrame(columns=["Date", "Equity"])

    events_df = pd.DataFrame(events).sort_values("Time").reset_index(drop=True)
    events_df["Equity"] = events_df["Delta"].cumsum()
    events_df = events_df.drop_duplicates(subset=["Time"], keep="last").reset_index(drop=True)

    return events_df.rename(columns={"Time": "Date"})[["Date", "Equity"]]


def _calc_daily_returns(equity_df):
    if equity_df.empty or len(equity_df) < 2:
        return pd.Series(dtype=float)
    daily = equity_df.set_index("Date").resample("D").ffill()
    daily["Return"] = daily["Equity"].pct_change()
    return daily["Return"].dropna()


def _calc_sharpe(daily_returns):
    if len(daily_returns) < 5 or daily_returns.std() == 0:
        return 0
    return float(daily_returns.mean() / daily_returns.std() * np.sqrt(252))


def _calc_max_drawdown(equity_df):
    if equity_df.empty:
        return 0, 0
    equity = equity_df["Equity"].values
    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    drawdown_pct = np.where(peak > 0, drawdown / peak * 100, 0)
    max_dd_idx = np.argmax(drawdown)
    return float(drawdown_pct[max_dd_idx]), float(drawdown[max_dd_idx])


def calc_daily_pl(trades):
    if trades.empty:
        return pd.DataFrame()

    df = trades.dropna(subset=["CloseTime"]).copy()
    df["Date"] = df["CloseTime"].dt.date
    daily = df.groupby("Date")["Profit"].sum().reset_index()
    daily["Date"] = pd.to_datetime(daily["Date"])
    daily = daily.sort_values("Date").reset_index(drop=True)
    daily["Cumulative"] = daily["Profit"].cumsum()
    return daily


def calc_account_summary(trades, account_col="Account"):
    if trades.empty or account_col not in trades.columns:
        return pd.DataFrame()

    summary = (
        trades.groupby(account_col)
        .agg(
            TradeCount=("Profit", "count"),
            TotalPL=("Profit", "sum"),
            WinCount=("Profit", lambda x: (x > 0).sum()),
            LossCount=("Profit", lambda x: (x < 0).sum()),
            GrossProfit=("Profit", lambda x: x[x > 0].sum()),
            GrossLoss=("Profit", lambda x: x[x < 0].sum()),
            AvgWin=("Profit", lambda x: x[x > 0].mean()),
            AvgLoss=("Profit", lambda x: x[x < 0].mean()),
        )
        .reset_index()
    )

    summary["WinRate"] = (summary["WinCount"] / summary["TradeCount"] * 100).round(1)
    summary["ProfitFactor"] = (
        abs(summary["GrossProfit"] / summary["GrossLoss"])
        .replace([float("inf")], float("inf"))
    )
    return summary
