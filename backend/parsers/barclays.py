"""
Barclays PDF statement parser.
Ported from ScrapeBanks/pdf.py and ScrapeBanks/bank_app.py::process_barclays_pdf().

Columns expected: Date | Description | Money out | Money in | Balance
Dates are in format '21 Feb' (no year) — year must be supplied or auto-detected.
"""

import re
import PyPDF2
import camelot
import numpy as np
import pandas as pd


HEADER_ROW = ["Date", "Description", "Money out", "Money in", "Balance"]
_HEADER_PATTERN = "|".join(h.lower() for h in HEADER_ROW)


def detect_year(pdf_path: str, filename: str = "") -> int:
    """Detect statement year from filename or PDF text. Falls back to current year."""
    from datetime import datetime

    # Filename pattern: Statement DD-MMM-YY ...
    if filename:
        m = re.search(r"(\d{2})-([A-Z]{3})-(\d{2})", filename.upper())
        if m:
            yy = int(m.group(3))
            return 2000 + yy if yy < 50 else 1900 + yy

    year_patterns = [
        r"your\s+balances?\s+on\s+\d+\s+\w+\s+(\d{4})",
        r"statement\s+date:?\s*\d+\s+\w+\s+(\d{4})",
        r"period\s+ending:?\s*\d+\s+\w+\s+(\d{4})",
    ]

    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = reader.pages[0].extract_text() if reader.pages else ""
            for pattern in year_patterns:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    year = int(m.group(1))
                    if 1900 <= year <= 2100:
                        return year
            m = re.search(r"\b(19|20)\d{2}\b", text[:500])
            if m:
                return int(m.group(0))
    except Exception:
        pass

    return datetime.now().year


def parse(pdf_path: str, statement_year: int) -> pd.DataFrame:
    """
    Parse a Barclays PDF and return a normalised DataFrame with columns:
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
        cleaned = cleaned.replace(",", "", regex=True)

        # Drop all-empty extra columns
        if len(cleaned.columns) > len(HEADER_ROW):
            empty_cols = [
                col
                for col in cleaned.columns
                if all(
                    pd.isna(v) or (isinstance(v, str) and not v.strip())
                    for v in cleaned.iloc[:, col]
                )
            ]
            for col in reversed(empty_cols):
                cleaned = cleaned.drop(cleaned.columns[col], axis=1)

            if len(cleaned.columns) > len(HEADER_ROW):
                cleaned = cleaned.iloc[:, : len(HEADER_ROW)]

        cleaned.columns = range(len(cleaned.columns))
        all_cleaned.append(cleaned)

    if not all_cleaned:
        raise ValueError("No transaction tables found in PDF")

    df = pd.concat(all_cleaned, ignore_index=True)
    df.columns = HEADER_ROW

    # Clean whitespace
    df = df.map(lambda x: str(x).strip() if pd.notnull(x) else x)
    df = df.replace({"": np.nan})

    # Merge continuation rows (no date, no money cols)
    to_drop = []
    for i in range(1, len(df)):
        row = df.iloc[i]
        if pd.isna(row["Date"]) and pd.isna(row[["Money out", "Money in", "Balance"]]).all():
            extra = str(row["Description"]) if pd.notna(row["Description"]) else ""
            if extra:
                df.at[i - 1, "Description"] = f"{df.at[i - 1, 'Description']}\n{extra}".strip()
            to_drop.append(i)
    df = df.drop(index=to_drop).reset_index(drop=True)

    # Numeric columns
    for col in ["Money out", "Money in", "Balance"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Date parsing (format: '21 Feb', year inferred)
    def _parse_date(date_str):
        if pd.isna(date_str) or not str(date_str).strip():
            return pd.NaT
        try:
            d = pd.to_datetime(str(date_str).strip(), format="%d %b", errors="coerce")
            if pd.isna(d):
                return pd.NaT
            d = d.replace(year=statement_year)
            return d
        except Exception:
            return pd.NaT

    df["Date"] = df["Date"].apply(_parse_date)
    df["Date"] = df["Date"].ffill()

    # Drop balance-only rows (no money movement)
    df = df[
        ~(
            (df["Money out"].isna() | (df["Money out"] == 0))
            & (df["Money in"].isna() | (df["Money in"] == 0))
            & df["Balance"].notna()
        )
    ].reset_index(drop=True)

    df = df.replace({np.nan: 0})

    # Normalise to unified amount: negative = out, positive = in
    result = pd.DataFrame()
    result["date"] = pd.to_datetime(df["Date"])
    result["description"] = df["Description"].astype(str)
    result["amount"] = df["Money in"] - df["Money out"]
    result["balance"] = df["Balance"]

    return result.dropna(subset=["date"])
