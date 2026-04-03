"""
Chase PDF statement parser.
Ported from ScrapeBanks/pdf_chase.py and ScrapeBanks/bank_app.py::process_chase_pdf().

Columns expected: Date | Transaction details | Amount | Balance
Chase uses full dates ('21 Jun 2025') and signed amounts ('+100.00' / '-50.00').
"""

import camelot
import numpy as np
import pandas as pd


HEADER_ROW = ["Date", "Transaction details", "Amount", "Balance"]
_HEADER_PATTERN = "|".join(h.lower() for h in HEADER_ROW)


def parse(pdf_path: str) -> pd.DataFrame:
    """
    Parse a Chase PDF and return a normalised DataFrame with columns:
        date (datetime), description (str), amount (float), balance (float)

    amount is negative for money-out, positive for money-in.
    """
    tables = camelot.read_pdf(pdf_path, flavor="stream", pages="all")
    all_cleaned = []

    for table in tables:
        df = table.df.copy()
        header_index = None

        for idx, row in df.iterrows():
            line = "|".join(str(x).strip().lower() for x in row if str(x).strip())
            if line == _HEADER_PATTERN:
                header_index = idx
                break

        if header_index is None:
            continue

        cleaned = df.iloc[header_index + 1 :].reset_index(drop=True)
        cleaned = cleaned.map(lambda x: str(x).strip() if pd.notnull(x) else x)
        cleaned = cleaned.replace(["£", ","], "", regex=True)
        cleaned = cleaned.replace({"": np.nan})
        cleaned = cleaned.dropna(axis=1, how="all")
        cleaned.columns = HEADER_ROW
        all_cleaned.append(cleaned)

    if not all_cleaned:
        raise ValueError("No transaction tables found in PDF")

    df = pd.concat(all_cleaned, ignore_index=True)
    df = df.map(lambda x: str(x).strip() if pd.notnull(x) else x)
    df = df.replace({"": np.nan})

    # Merge continuation rows
    to_drop = []
    for i in range(1, len(df)):
        row = df.iloc[i]
        if pd.isna(row["Date"]) and pd.isna(row[["Amount", "Balance"]]).all():
            extra = str(row["Transaction details"]) if pd.notna(row["Transaction details"]) else ""
            if extra:
                df.at[i - 1, "Transaction details"] = (
                    f"{df.at[i - 1, 'Transaction details']}\n{extra}".strip()
                )
            to_drop.append(i)
    df = df.drop(index=to_drop).reset_index(drop=True)

    # Split signed Amount into money_in / money_out then unify
    money_out = []
    money_in = []
    for val in df["Amount"]:
        s = str(val).strip()
        if not s or s == "nan":
            money_out.append(np.nan)
            money_in.append(np.nan)
        elif s.startswith("-"):
            money_out.append(pd.to_numeric(s[1:], errors="coerce"))
            money_in.append(np.nan)
        elif s.startswith("+"):
            money_out.append(np.nan)
            money_in.append(pd.to_numeric(s[1:], errors="coerce"))
        else:
            money_out.append(np.nan)
            money_in.append(pd.to_numeric(s, errors="coerce"))

    df["_out"] = money_out
    df["_in"] = money_in

    for col in ["_out", "_in", "Balance"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y", errors="coerce")

    # Drop balance-only rows
    df = df[~(df["_out"].isna() & df["_in"].isna())].reset_index(drop=True)
    df = df[~df["Description"].isin(["Closing balance", "Opening balance"])].reset_index(drop=True)
    df = df.rename(columns={"Transaction details": "Description"})

    result = pd.DataFrame()
    result["date"] = df["Date"]
    result["description"] = df["Description"].astype(str)
    result["amount"] = df["_in"].fillna(0) - df["_out"].fillna(0)
    result["balance"] = df["Balance"]

    return result.dropna(subset=["date"])
