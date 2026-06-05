from datetime import datetime

ACCOUNT_TYPE = "cent"
CENT_DIVISOR = 100.0

INITIAL_CAPITAL = 2000.0

DEPOSITS = [
    {"date": datetime(2026, 5, 28), "amount": 675.0},
]

DATA_DIR = "data"

ACCOUNT_START_DATES = {
    "ReportHistory-26753637": datetime(2026, 3, 31),
}

ACCOUNT_LABELS = {
    "ReportHistory-26753637": "帳戶 1",
    "ReportHistory-27486062": "帳戶 2",
    "ReportHistory-28254096": "帳戶 3",
    "ReportHistory-29080824": "帳戶 4",
    "ReportHistory-29084110": "帳戶 5",
}

ACCOUNT_COLORS = [
    "#636efa", "#ef553b", "#00cc96", "#ab63fa", "#ffa15a",
]
