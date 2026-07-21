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

def build_stats(wo_df, deals_df):
    """Compact stats dict passed to Gemini instead of raw rows."""
    stats = {}

    if wo_df is not None and not wo_df.empty:
        stats["work_orders_total_rows"] = len(wo_df)
        if "Sector" in wo_df.columns:
            stats["top_sectors_wo"] = wo_df["Sector"].dropna().value_counts().head(8).to_dict()
        if "Execution Status" in wo_df.columns:
            stats["execution_status"] = wo_df["Execution Status"].dropna().value_counts().to_dict()
        for col in WO_MONEY_COLS:
            if col in wo_df.columns:
                s = wo_df[col].dropna()
                if not s.empty:
                    stats[col] = {"sum": fmt_inr(s.sum()), "mean": fmt_inr(s.mean()),
                                  "non_null_count": len(s)}

    if deals_df is not None and not deals_df.empty:
        stats["deals_total_rows"] = len(deals_df)
        if "stage_type" in deals_df.columns:
            stats["deals_by_stage_type"] = deals_df["stage_type"].value_counts().to_dict()
        if "Deal Stage" in deals_df.columns:
            stats["deal_stages"] = deals_df["Deal Stage"].dropna().value_counts().head(15).to_dict()
        if "Sector/service" in deals_df.columns:
            stats["top_sectors_deals"] = deals_df["Sector/service"].dropna().value_counts().head(8).to_dict()
        if DEALS_MONEY_COL in deals_df.columns and "stage_type" in deals_df.columns:
            open_df = deals_df[deals_df["stage_type"] == "open"]
            stats["open_pipeline_raw"] = fmt_inr(open_df[DEALS_MONEY_COL].dropna().sum())

            def get_weight(row):
                p = row.get("Closure Probability")
                if pd.notna(p):
                    n = pd.to_numeric(str(p).replace("%", ""), errors="coerce")
                    if pd.notna(n):
                        return float(n) / 100 if float(n) > 1 else float(n)
                label = str(row.get("Deal Status", "")).lower()
                return {"high": 0.70, "med": 0.40, "medium": 0.40, "low": 0.15}.get(label, 0.40)

            if not open_df.empty:
                weights = open_df.apply(get_weight, axis=1)
                vals = open_df[DEALS_MONEY_COL].fillna(0)
                stats["weighted_pipeline"] = fmt_inr((vals * weights).sum())

        if "stage_type" in deals_df.columns:
            won  = int((deals_df["stage_type"] == "won").sum())
            dead = int((deals_df["stage_type"] == "dead").sum())
            if won + dead > 0:
                stats["win_rate"] = f"{won/(won+dead)*100:.1f}% ({won} won / {dead} lost)"

    recv_col = "Amount Receivable (Masked)"
    if wo_df is not None and recv_col in wo_df.columns:
        stats["collections_outstanding"] = fmt_inr(wo_df[recv_col].dropna().sum())

    return stats
