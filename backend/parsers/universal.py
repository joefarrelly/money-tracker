"""
Universal bank statement parser.

Instead of hardcoding column names per bank, this module:
  1. Extracts all tables from the PDF via camelot
  2. Scores each row/column against heuristics to find the transaction table
     and infer which column plays which role (date, description, amount, balance)
  3. Tries to match against saved StatementFormats before falling back to heuristics
  4. Returns a preview payload the user can confirm or adjust before importing

Roles:
  date         — transaction date column
  description  — narrative / payee column
  money_in     — credit column (split-style, e.g. Barclays)
  money_out    — debit column  (split-style)
  amount       — signed amount column (e.g. Chase "+100.00" / "-50.00")
  balance      — running balance column
  ignore       — column should be skipped
"""

import os
import re
import sys

import camelot
import numpy as np
import pandas as pd
import PyPDF2

# Ordered list of date formats to try, paired with year_source hint
DATE_FORMATS = [
    ("%d %b %Y", "inline"),   # 21 Jun 2025  — Chase
    ("%d/%m/%Y", "inline"),   # 21/06/2025
    ("%Y-%m-%d", "inline"),   # 2025-06-21
    ("%d-%m-%Y", "inline"),   # 21-06-2025
    ("%d/%m/%y", "inline"),   # 21/06/25
    ("%d %b", "detect"),      # 21 Feb  — Barclays (year must come from elsewhere)
]

# Keywords that signal a column role (lowercase)
ROLE_KEYWORDS: dict[str, list[str]] = {
    "date": ["date", "posted", "value date", "txn date", "trans date"],
    "description": [
        "description", "details", "narrative", "particulars",
        "reference", "transaction details", "transaction",
    ],
    "money_in": ["money in", "credit", "paid in", "received", "deposit", "in"],
    "money_out": ["money out", "debit", "paid out", "withdrawal", "charge", "out"],
    "amount": ["amount", "value", "sum"],
    "balance": ["balance", "running balance", "running total"],
}

# Number of words to try when splitting a merged "date description" value
_DATE_WORD_COUNTS = [3, 2, 4]


# ── Text extraction ───────────────────────────────────────────────────────────

def _extract_text(pdf_path: str) -> str:
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(
                (page.extract_text() or "") for page in reader.pages[:4]
            )
    except Exception:
        return ""


def detect_account_number(text: str) -> str | None:
    patterns = [
        r"account\s+(?:number|no\.?):?\s*(\d[\d\s-]{5,20})",
        r"(?:a/c|acc(?:ount)?)\s*(?:number|no\.?)?:?\s*(\d[\d\s-]{5,20})",
        r"\b(\d{8})\b",  # bare 8-digit number — common UK current accounts
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = re.sub(r"[\s-]", "", m.group(1))
            if 6 <= len(val) <= 16:
                return val
    return None


def detect_year(pdf_path: str, text: str, filename: str = "") -> int | None:
    """Try to find the statement year from filename, then PDF text."""
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
    for pat in year_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            year = int(m.group(1))
            if 1990 <= year <= 2100:
                return year

    m = re.search(r"\b(19|20)\d{2}\b", text[:500])
    if m:
        return int(m.group(0))

    return None


# ── Header detection ──────────────────────────────────────────────────────────

def _score_as_header(row: pd.Series) -> float:
    """Return a 0–1 score for how likely this row is a column-header row."""
    cells = [str(v).strip() for v in row if str(v).strip()]
    if len(cells) < 2:
        return 0.0

    # Headers are short strings (not long descriptions or numbers)
    avg_len = sum(len(c) for c in cells) / len(cells)
    if avg_len > 35:
        return 0.0

    # Headers shouldn't be mostly numeric
    numeric = sum(1 for c in cells if re.match(r"^[\d.,+\-£$€%\s]+$", c))
    if numeric / len(cells) > 0.5:
        return 0.0

    # Headers shouldn't look like dates
    date_like = 0
    for c in cells:
        for fmt, _ in DATE_FORMATS[:4]:
            try:
                pd.to_datetime(c, format=fmt)
                date_like += 1
                break
            except Exception:
                pass
    if date_like / len(cells) > 0.4:
        return 0.0

    # Bonus for recognised column-name keywords
    all_text = " ".join(cells).lower()
    keyword_hits = sum(
        1
        for kws in ROLE_KEYWORDS.values()
        for kw in kws
        if kw in all_text
    )
    return 0.4 + min(keyword_hits * 0.1, 0.55)


def _find_header_row(df: pd.DataFrame) -> int | None:
    """Return the index of the most header-like row, or None if score < threshold."""
    best_score = 0.39  # minimum threshold
    best_idx = None
    for idx, row in df.iterrows():
        score = _score_as_header(row)
        if score > best_score:
            best_score = score
            best_idx = idx
    return best_idx


def _score_column_efficiency(df: pd.DataFrame, header_idx: int) -> float:
    """
    Return the fraction of columns that are meaningfully populated in data rows.
    Penalises tables like page-1 summary pages that have many empty/sparse columns.
    """
    data = df.iloc[header_idx + 1:].head(10)
    if len(data) == 0:
        return 0.0
    used = 0
    for col in data.columns:
        non_empty = sum(
            1 for v in data[col]
            if str(v).strip() and str(v).strip() not in ("nan", "")
        )
        if non_empty / len(data) > 0.3:
            used += 1
    return used / len(data.columns) if len(data.columns) > 0 else 0.0


# ── Column role inference ─────────────────────────────────────────────────────

def _classify_column(name: str, values: list[str]) -> str:
    name_lower = name.lower().strip()

    # Name-based (most reliable) — longest keyword match wins
    best_role = None
    best_kw_len = 0
    for role, keywords in ROLE_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower and len(kw) > best_kw_len:
                best_role = role
                best_kw_len = len(kw)

    # If both "date" and "description" keywords appear in the same header,
    # or if the data looks like merged date+description, flag it
    date_in_name = any(kw in name_lower for kw in ROLE_KEYWORDS["date"])
    desc_in_name = any(kw in name_lower for kw in ROLE_KEYWORDS["description"])
    if date_in_name and desc_in_name:
        return "date_description"

    if best_role:
        return best_role

    # Data-based fallback — sample first 20 non-empty values
    non_empty = [v for v in values if v and v not in ("nan", "")]
    if not non_empty:
        return "ignore"
    sample = non_empty[:20]

    # Merged date+description? (e.g. "01 Sep 2025 Opening balance")
    if _is_merged_date_description(sample):
        return "date_description"

    # Date-like?
    date_hits = 0
    for v in sample:
        for fmt, _ in DATE_FORMATS:
            try:
                pd.to_datetime(v, format=fmt)
                date_hits += 1
                break
            except Exception:
                pass
    if date_hits / len(sample) > 0.5:
        return "date"

    # Numeric?
    cleaned = [re.sub(r"[£$€,\s]", "", v) for v in sample]
    numeric_hits = sum(1 for v in cleaned if re.match(r"^[+\-]?\d+\.?\d*$", v))
    if numeric_hits / len(cleaned) > 0.6:
        # Signed (+/-) → probably amount
        signed = sum(1 for v in cleaned if v.startswith("+") or v.startswith("-"))
        if signed / len(cleaned) > 0.25:
            return "amount"
        return "balance"

    # Long text → description
    avg_len = sum(len(v) for v in sample) / len(sample)
    if avg_len > 8:
        return "description"

    return "ignore"


def _infer_mapping(column_headers: list[str], data_rows: pd.DataFrame) -> dict:
    """Return a column-mapping dict inferred from headers + sample data."""
    roles: dict[int, str] = {}
    for i, header in enumerate(column_headers):
        if i >= len(data_rows.columns):
            break
        values = [str(v).strip() for v in data_rows.iloc[:, i]]
        roles[i] = _classify_column(header, values)

    def first_of(role: str) -> int | None:
        for idx, r in roles.items():
            if r == role:
                return idx
        return None

    amount_style = (
        "split"
        if (first_of("money_in") is not None or first_of("money_out") is not None)
        else "signed"
    )

    # Detect date format from sample values in the date column (or merged column)
    date_format = "%d %b %Y"
    year_source = "inline"
    date_col = first_of("date")
    date_description_col = first_of("date_description")
    probe_col = date_col if date_col is not None else date_description_col
    if probe_col is not None:
        raw_vals = [
            str(v).strip()
            for v in data_rows.iloc[:8, probe_col]
            if str(v).strip() and str(v).strip() not in ("nan", "")
        ]
        # For merged columns, extract just the date prefix for format detection
        sample_dates = []
        for v in raw_vals:
            words = v.split()
            for n in _DATE_WORD_COUNTS:
                candidate = " ".join(words[:n])
                found = False
                for fmt, _ in DATE_FORMATS:
                    if _try_parse(candidate, fmt):
                        sample_dates.append(candidate)
                        found = True
                        break
                if found:
                    break
            else:
                sample_dates.append(v)  # fallback: try whole value
        for fmt, src in DATE_FORMATS:
            hits = sum(
                1
                for v in sample_dates
                if _try_parse(v, fmt)
            )
            if hits >= min(2, len(sample_dates)):
                date_format = fmt
                year_source = src
                break

    mapping: dict = {
        "date_col": date_col,
        "description_col": first_of("description"),
        "date_description_col": date_description_col,
        "balance_col": first_of("balance"),
        "amount_style": amount_style,
        "date_format": date_format,
        "year_source": year_source,
    }

    if amount_style == "split":
        mapping["money_in_col"] = first_of("money_in")
        mapping["money_out_col"] = first_of("money_out")
        mapping["amount_col"] = None
    else:
        mapping["amount_col"] = first_of("amount")
        mapping["money_in_col"] = None
        mapping["money_out_col"] = None

    return mapping


def _try_parse(value: str, fmt: str) -> bool:
    try:
        pd.to_datetime(value, format=fmt)
        return True
    except Exception:
        return False


def _is_merged_date_description(values: list[str]) -> bool:
    """Return True if most values look like a date prefix followed by description text."""
    hits = 0
    for v in values[:15]:
        words = v.split()
        if len(words) < 2:
            continue
        for n in _DATE_WORD_COUNTS:
            if len(words) <= n:
                continue
            date_str = " ".join(words[:n])
            for fmt, _ in DATE_FORMATS:
                if _try_parse(date_str, fmt) and len(words) > n:
                    hits += 1
                    break
            else:
                continue
            break
    return hits / max(len(values[:15]), 1) > 0.5


def split_date_description(value: str, date_fmt: str, year: int | None = None):
    """
    Split a merged value like "01 Sep 2025 Opening balance" into (Timestamp, str).
    Returns (NaT, original_value) if no date prefix is found.
    """
    words = str(value).strip().split()
    for n in _DATE_WORD_COUNTS:
        if len(words) <= n:
            continue
        date_str = " ".join(words[:n])
        try:
            d = pd.to_datetime(date_str, format=date_fmt, errors="raise")
            if "%Y" not in date_fmt and year:
                d = d.replace(year=year)
            description = " ".join(words[n:])
            return d, description
        except Exception:
            pass
    return pd.NaT, str(value).strip()


# ── Format matching ───────────────────────────────────────────────────────────

def match_saved_format(column_headers: list[str], formats: list) -> tuple:
    """
    Try to match column_headers against a list of StatementFormat ORM objects.
    Returns (best_format | None, confidence 0-1).
    """
    headers_lower = [h.lower().strip() for h in column_headers]

    best_fmt = None
    best_score = 0.0

    for fmt in formats:
        fmt_headers = [h.lower().strip() for h in (fmt.column_headers or [])]
        if not fmt_headers:
            continue

        if fmt_headers == headers_lower:
            return fmt, 0.95

        # Partial overlap score
        common = sum(1 for h in headers_lower if h in fmt_headers)
        score = common / max(len(fmt_headers), len(headers_lower))
        if score > best_score:
            best_score = score
            best_fmt = fmt

    if best_score >= 0.7:
        return best_fmt, best_score

    return None, 0.0


# ── Public API ────────────────────────────────────────────────────────────────

def _read_tables(pdf_path: str) -> list:
    """
    Try lattice flavor first (reliable for PDFs with table borders — e.g. Chase).
    Fall back to stream for borderless layouts (e.g. Barclays).
    """
    try:
        tables = camelot.read_pdf(pdf_path, flavor="lattice", pages="all")
        # Only use lattice results if we got meaningful data
        if len(tables) > 0 and any(len(t.df) > 3 for t in tables):
            return list(tables)
    except Exception:
        pass
    return list(camelot.read_pdf(pdf_path, flavor="stream", pages="all"))


def extract_preview(pdf_path: str, filename: str = "", saved_formats: list | None = None) -> dict:
    """
    Parse the PDF enough to return a preview payload.
    Does NOT write to the database.

    Returns:
        column_headers  — list of raw header strings
        proposed_mapping — best-guess column mapping dict
        matched_format   — matched StatementFormat ORM object (or None)
        confidence       — 0-1 match confidence
        detected_account_number
        detected_year
        needs_year       — True if date format has no year component
        sample_rows      — first 8 data rows (list of string lists)
        total_rows       — total rows in the transaction table
    """
    text = _extract_text(pdf_path)
    detected_account = detect_account_number(text)
    detected_year = detect_year(pdf_path, text, filename)

    tables = _read_tables(pdf_path)

    best_df = None
    best_header_idx = None
    best_score = 0.0
    best_col_count = 0
    total_rows_all_pages = 0

    for table in tables:
        df = table.df
        idx = _find_header_row(df)
        if idx is None:
            continue
        header_score = _score_as_header(df.iloc[idx])
        if header_score < 0.39:
            continue
        efficiency = _score_column_efficiency(df, idx)
        # Weight efficiency heavily — avoids sparse cover/summary pages
        combined = header_score * 0.35 + efficiency * 0.65
        if combined > best_score:
            best_score = combined
            best_df = df
            best_header_idx = idx
            best_col_count = len(df.columns)

    if best_df is None:
        raise ValueError("No transaction table found in this PDF")

    # Count data rows across all tables that match the best table's column count
    for table in tables:
        df = table.df
        if len(df.columns) != best_col_count:
            continue
        idx = _find_header_row(df)
        if idx is not None:
            total_rows_all_pages += len(df) - idx - 1
        else:
            total_rows_all_pages += len(df)

    raw_headers = [str(v).strip() for v in best_df.iloc[best_header_idx]]
    # Trim trailing empty headers
    while raw_headers and not raw_headers[-1]:
        raw_headers.pop()

    data_rows = best_df.iloc[best_header_idx + 1:].reset_index(drop=True)
    if len(data_rows.columns) > len(raw_headers):
        data_rows = data_rows.iloc[:, : len(raw_headers)]

    # Try to match a saved format first
    matched_fmt = None
    confidence = 0.0
    if saved_formats:
        matched_fmt, confidence = match_saved_format(raw_headers, saved_formats)

    if matched_fmt and confidence >= 0.9:
        # High-confidence match — use saved mapping directly
        proposed = {
            "date_col": matched_fmt.date_col,
            "description_col": matched_fmt.description_col,
            "balance_col": matched_fmt.balance_col,
            "amount_style": matched_fmt.amount_style,
            "amount_col": matched_fmt.amount_col,
            "money_in_col": matched_fmt.money_in_col,
            "money_out_col": matched_fmt.money_out_col,
            "date_format": matched_fmt.date_format,
            "year_source": matched_fmt.year_source,
        }
    else:
        proposed = _infer_mapping(raw_headers, data_rows)

    sample = []
    for _, row in data_rows.head(8).iterrows():
        vals = [str(v).strip() for v in row]
        if any(v for v in vals):
            sample.append(vals)

    needs_year = "%Y" not in proposed.get("date_format", "")

    return {
        "column_headers": raw_headers,
        "proposed_mapping": proposed,
        "matched_format": matched_fmt,
        "confidence": round(confidence, 2),
        "detected_account_number": detected_account,
        "detected_year": detected_year,
        "needs_year": needs_year,
        "sample_rows": sample,
        "total_rows": total_rows_all_pages,
    }


def parse_with_mapping(
    pdf_path: str,
    mapping: dict,
    year: int | None = None,
    skip_patterns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Parse the full PDF using a confirmed column mapping.
    Returns a normalised DataFrame: date, description, amount, balance.
    """
    has_date = mapping.get("date_col") is not None or mapping.get("date_description_col") is not None
    has_desc = mapping.get("description_col") is not None or mapping.get("date_description_col") is not None
    if not has_date:
        raise ValueError("No date column assigned — please assign one in the column mapping")
    if not has_desc:
        raise ValueError("No description column assigned — please assign one in the column mapping")

    tables = _read_tables(pdf_path)
    all_frames = []

    # The minimum number of columns required: must contain every column index in the mapping
    required_col_indices = [
        mapping.get(k)
        for k in ("date_col", "description_col", "date_description_col",
                  "balance_col", "amount_col", "money_in_col", "money_out_col")
        if mapping.get(k) is not None
    ]
    needed_cols = max(required_col_indices) + 1 if required_col_indices else 1

    print(f"[parse_with_mapping] tables={len(tables)} needed_cols={needed_cols} mapping={mapping}", file=sys.stderr)

    for i, table in enumerate(tables):
        df = table.df
        cols_ok = len(df.columns) >= needed_cols
        header_idx = _find_header_row(df)
        print(f"  table[{i}] shape={df.shape} cols_ok={cols_ok} header_row={header_idx}", file=sys.stderr)
        if not cols_ok:
            continue
        if header_idx is not None:
            data = df.iloc[header_idx + 1:].reset_index(drop=True)
        else:
            # No repeated header on this page — include all rows and let
            # date/amount parsing filter out non-transaction rows
            data = df.reset_index(drop=True)
        if len(data) == 0:
            continue
        all_frames.append(data)

    print(f"[parse_with_mapping] frames_collected={len(all_frames)} total_rows={sum(len(f) for f in all_frames)}", file=sys.stderr)

    if not all_frames:
        raise ValueError("No transaction data found in PDF")

    df = pd.concat(all_frames, ignore_index=True)
    df = df.map(lambda x: str(x).strip() if pd.notnull(x) else x)
    df = df.replace({"": np.nan}).infer_objects(copy=False)
    # Strip currency symbols and commas from all cells
    df = df.replace(r"[£$€,]", "", regex=True)

    date_col = mapping.get("date_col")
    desc_col = mapping.get("description_col")
    date_desc_col = mapping.get("date_description_col")
    bal_col = mapping.get("balance_col")
    amount_style = mapping["amount_style"]
    date_fmt = mapping["date_format"]

    # Parse dates
    def _parse_date(v):
        if pd.isna(v) or not str(v).strip():
            return pd.NaT
        s = str(v).strip()
        try:
            d = pd.to_datetime(s, format=date_fmt, errors="coerce")
            if pd.isna(d):
                return pd.NaT
            if "%Y" not in date_fmt and year:
                d = d.replace(year=year)
            return d
        except Exception:
            return pd.NaT

    if date_desc_col is not None:
        # Merged column: split date prefix from description text
        parsed = [split_date_description(v, date_fmt, year) for v in df.iloc[:, date_desc_col].astype(str)]
        df["_date"] = pd.Series([p[0] for p in parsed], index=df.index)
        df["_description"] = pd.Series([p[1] for p in parsed], index=df.index)
    else:
        df["_date"] = df.iloc[:, date_col].apply(_parse_date)
        df["_description"] = df.iloc[:, desc_col].astype(str)

    df["_date"] = df["_date"].ffill()

    df["_balance"] = (
        pd.to_numeric(df.iloc[:, bal_col], errors="coerce")
        if bal_col is not None
        else np.nan
    )

    if amount_style == "split":
        in_col = mapping.get("money_in_col")
        out_col = mapping.get("money_out_col")
        money_in = (
            pd.to_numeric(df.iloc[:, in_col], errors="coerce").fillna(0)
            if in_col is not None
            else pd.Series(0, index=df.index)
        )
        money_out = (
            pd.to_numeric(df.iloc[:, out_col], errors="coerce").fillna(0)
            if out_col is not None
            else pd.Series(0, index=df.index)
        )
        df["_amount"] = money_in - money_out
    else:
        amt_col = mapping.get("amount_col")
        if amt_col is not None:
            raw = df.iloc[:, amt_col].astype(str).str.replace(r"[£$€,\s]", "", regex=True)
            df["_amount"] = pd.to_numeric(raw, errors="coerce")
        else:
            df["_amount"] = np.nan

    # Drop rows with no real transaction
    df = df[df["_amount"].notna() & (df["_amount"] != 0)].reset_index(drop=True)

    result = pd.DataFrame({
        "date": df["_date"],
        "description": df["_description"],
        "amount": df["_amount"],
        "balance": df["_balance"],
    })

    result = result.dropna(subset=["date"])

    if skip_patterns:
        active = [p.strip() for p in skip_patterns if p.strip()]
        if active:
            pattern = "|".join(re.escape(p) for p in active)
            result = result[~result["description"].str.contains(pattern, case=False, na=False)]

    return result
