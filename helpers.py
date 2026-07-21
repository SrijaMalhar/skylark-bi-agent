import pandas as pd

WO_MONEY_COLS = [
    "Amount in Rupees (Excl of GST) (Masked)",
    "Billed Value...(Masked)",
    "Collected Amount...(Masked)",
    "Amount Receivable (Masked)",
]
DEALS_MONEY_COL = "Masked Deal value"


def fmt_inr(val):
    if val >= 1e7:
        return f"\u20b9{val/1e7:.2f} Cr"
    if val >= 1e5:
        return f"\u20b9{val/1e5:.2f} L"
    return f"\u20b9{val:,.0f}"


def clean_work_orders(df):
    # drop stray header rows (the cell literally equals the column name)
    for col in ["Sector", "Execution Status", "Nature of Work", "Type of Work"]:
        if col in df.columns:
            df = df[df[col].astype(str).str.strip() != col]

    for col in WO_MONEY_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # normalize so "mining" and "Mining" are treated the same
    for col in ["Sector", "Execution Status"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
            df[col] = df[col].replace("Nan", pd.NA)

    return df.reset_index(drop=True)

def clean_deals(df):
    for col in ["Deal Stage", "Sector/service", "Deal Status"]:
        if col in df.columns:
            df = df[df[col].astype(str).str.strip() != col]

    if DEALS_MONEY_COL in df.columns:
        df[DEALS_MONEY_COL] = pd.to_numeric(df[DEALS_MONEY_COL], errors="coerce")

    for col in ["Tentative Close Date", "Created Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in ["Sector/service", "Deal Status"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
            df[col] = df[col].replace("Nan", pd.NA)

    # L/N/O = dead, G/H/J/K = won, everything else = open
    if "Deal Stage" in df.columns:
        def classify(stage):
            if pd.isna(stage):
                return "unknown"
            p = str(stage).strip()[:2]
            if p in ("L.", "N.", "O."):
                return "dead"
            if p in ("G.", "H.", "J.", "K.") or "project completed" in str(stage).lower():
                return "won"
            return "open"
        df["stage_type"] = df["Deal Stage"].apply(classify)

    return df.reset_index(drop=True)
