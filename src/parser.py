from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup


def parse_mt4_html(filepath, account_label=None, cent_divisor=1.0):
    with open(filepath, "rb") as f:
        raw = f.read()
    soup = BeautifulSoup(raw, "html.parser")
    rows = soup.find_all("tr")

    trade_records = []
    balance_records = []

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 15:
            continue

        typ = cells[3].get_text(strip=True)
        profit_str = cells[12].get_text(strip=True).replace(" ", "").replace(",", "")
        time_str = cells[0].get_text(strip=True)

        try:
            profit = float(profit_str) if profit_str else 0.0
        except ValueError:
            continue

        if typ in ("sell", "buy") and profit != 0.0:
            trend = cells[4].get_text(strip=True)
            orig_type = (
                "sell" if typ == "buy" and trend == "out"
                else "buy" if typ == "sell" and trend == "out"
                else typ
            )
            rec = {
                "CloseTime": time_str,
                "Ticket": cells[1].get_text(strip=True),
                "Item": cells[2].get_text(strip=True),
                "Type": orig_type,
                "Size": _parse_num(cells[5].get_text(strip=True)) / cent_divisor,
                "ClosePrice": cells[6].get_text(strip=True),
                "Commission": _parse_num(cells[9].get_text(strip=True)) / cent_divisor,
                "Swap": _parse_num(cells[11].get_text(strip=True)) / cent_divisor,
                "Profit": profit / cent_divisor,
            }
            trade_records.append(rec)

        elif typ in ("balance", "deposit", "withdrawal", "credit", "bonus"):
            comment = cells[14].get_text(strip=True) if len(cells) > 14 else ""
            rec = {
                "Time": time_str,
                "Type": typ,
                "Profit": profit / cent_divisor,
                "Comment": comment[:80],
            }
            balance_records.append(rec)

    if not trade_records:
        return None

    df = pd.DataFrame(trade_records)
    _convert_trade_dtypes(df)

    if account_label:
        df["Account"] = str(account_label)

    if balance_records:
        bal_df = pd.DataFrame(balance_records)
        bal_df["Time"] = pd.to_datetime(bal_df["Time"], errors="coerce")
        bal_df["Profit"] = pd.to_numeric(
            bal_df["Profit"].astype(str).str.replace(",", "").str.strip(), errors="coerce"
        ).fillna(0).astype(float)
        if account_label:
            bal_df["Account"] = str(account_label)
        df.attrs["balance_events"] = bal_df
    else:
        df.attrs["balance_events"] = None

    return df


def _convert_trade_dtypes(df):
    for col in ["Profit", "Swap", "Commission", "Size"]:
        if col in df.columns:
            df[col] = (
                pd.to_numeric(
                    df[col].astype(str).str.replace(",", "").str.strip(),
                    errors="coerce",
                )
                .fillna(0)
                .astype(float)
            )

    if "CloseTime" in df.columns:
        df["CloseTime"] = pd.to_datetime(df["CloseTime"], errors="coerce")

    return df


def _parse_num(s):
    try:
        return float(s.replace(",", "").strip()) if s.strip() else 0.0
    except ValueError:
        return 0.0


def load_all_accounts(data_dir, cent_divisor=1.0):
    data_path = Path(data_dir)
    html_files = sorted(data_path.glob("*.html"))

    if not html_files:
        return pd.DataFrame()

    all_trades = []
    all_balances = []

    for fp in html_files:
        if fp.suffix.lower() != ".html":
            continue
        label = fp.stem
        df = parse_mt4_html(str(fp), account_label=label, cent_divisor=cent_divisor)
        if df is not None and len(df) > 0:
            all_trades.append(df)
            bal = df.attrs.get("balance_events")
            if bal is not None and len(bal) > 0:
                all_balances.append(bal)

    if not all_trades:
        return pd.DataFrame()

    for d in all_trades:
        d.attrs.clear()
    combined = pd.concat(all_trades, ignore_index=True)
    combined = combined.sort_values("CloseTime", na_position="last").reset_index(drop=True)

    if all_balances:
        bal_all = pd.concat(all_balances, ignore_index=True)
        combined.attrs["balance_events"] = bal_all.sort_values("Time").reset_index(drop=True)
    else:
        combined.attrs["balance_events"] = None

    return combined
