"""
Payslip PDF parser for NordHealth / Provet Cloud payslips.

Handles two table layouts produced by camelot stream mode:
  - 5-column (2022):  Description | Rate | Units Due | Amount | This Year
  - 4-column (2023+): Description | Rate/Units | Amount | This Year

Returns a dict ready to be stored as a Salary + PayslipLineItem records.
"""

from __future__ import annotations

import re
from datetime import datetime, date


def _parse_amount(text: str) -> float | None:
    if not text:
        return None
    cleaned = (
        str(text).strip()
        .replace(",", "")
        .replace("£", "")
        .replace("(", "-")
        .replace(")", "")
    )
    if not cleaned or cleaned in ("-", "0", ""):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _cell(row, idx: int) -> str:
    try:
        return str(row[idx]).strip()
    except (IndexError, KeyError):
        return ""


def _row_contains(row, keyword: str) -> bool:
    return any(keyword.upper() in _cell(row, i).upper() for i in range(len(row)))


def parse_payslip_pdf(filepath: str) -> dict:
    """
    Parse a payslip PDF and return structured data.

    Returns:
        {
            'date': date | None,
            'employer': str,
            'line_items': [
                {
                    'description': str,
                    'rate': float | None,
                    'units': str | None,
                    'amount': float,
                    'this_year_amount': float | None,
                    'line_type': 'earning' | 'deduction',
                }
            ],
            'net_pay': float,
            'gross_pay': float,       # sum of earnings
            'total_deductions': float,
            'taxable_to_date': float | None,
        }
    """
    import camelot  # local import so the module loads without camelot

    tables = camelot.read_pdf(filepath, pages="all", flavor="stream")
    if not tables:
        raise ValueError("No tables found in PDF")

    df = tables[0].df
    n_cols = len(df.columns)

    # ── Find header row ────────────────────────────────────────────────────────
    header_row_idx = None
    for i, row in df.iterrows():
        if "DESCRIPTION" in _cell(row, 0).upper():
            header_row_idx = i
            break

    if header_row_idx is None:
        raise ValueError("Could not find DESCRIPTION header in payslip")

    header = df.iloc[header_row_idx]

    # ── Identify column roles from header ──────────────────────────────────────
    amount_col = None
    this_year_col = None

    for c in range(n_cols):
        h = _cell(header, c).upper()
        if "AMOUNT" in h:
            amount_col = c
        if "THIS YEAR" in h or ("YEAR" in h and "AMOUNT" not in h):
            this_year_col = c

    if amount_col is None:
        raise ValueError("Could not identify AMOUNT column in payslip header")

    # ── Extract employer, NI number & date from pre-header rows ──────────────
    employer = ""
    ni_number = ""
    pay_date: date | None = None

    for i in range(header_row_idx):
        row = df.iloc[i]
        row_text = " ".join(_cell(row, c) for c in range(n_cols))

        if i == 0:
            # Employer: last non-empty cell
            for c in range(n_cols - 1, -1, -1):
                val = _cell(row, c)
                if val:
                    employer = val
                    break

        # NI number: "NI Letter & No: A PB175845B" → "PB175845B"
        # Format: NI letter (category), then NI number (2 letters + 6 digits + 1 letter)
        ni_match = re.search(r"NI Letter & No:\s*[A-Z]\s+([A-Z]{2}\d{6}[A-Z])", row_text)
        if ni_match and not ni_number:
            ni_number = ni_match.group(1)

        # Date: look for "Date: DD/MM/YYYY"
        date_match = re.search(r"Date:\s*(\d{2}/\d{2}/\d{4})", row_text)
        if date_match and pay_date is None:
            pay_date = datetime.strptime(date_match.group(1), "%d/%m/%Y").date()

    # ── Parse line items ───────────────────────────────────────────────────────
    line_items: list[dict] = []
    past_total = False
    net_pay = 0.0
    taxable_to_date: float | None = None

    SKIP_PATTERNS = re.compile(
        r"^(Ers NIC|Ers Pension|Tax District|Tax Reference|Tax:)",
        re.IGNORECASE,
    )

    for i in range(header_row_idx + 1, len(df)):
        row = df.iloc[i]
        all_cells = " ".join(_cell(row, c) for c in range(n_cols))

        # NET PAY detection — check first, before any other filtering
        if "NET PAY" in all_cells.upper():
            amt = _parse_amount(_cell(row, amount_col))
            if amt is not None:
                net_pay = amt
            continue

        # TOTAL row — marks boundary between earnings and deductions
        if any(_cell(row, c).strip().upper() == "TOTAL" for c in range(n_cols)):
            past_total = True
            continue

        desc = _cell(row, 0)

        # Skip empty or boilerplate rows
        if not desc or SKIP_PATTERNS.match(desc):
            continue

        # "Tax:\n0.00" rows
        if desc.upper().startswith("TAX:") or desc.upper().startswith("NOTE:"):
            continue

        # "Total taxable pay to date: X"
        if "total taxable pay" in desc.lower():
            m = re.search(r"([\d,]+\.\d+)", desc)
            if m:
                taxable_to_date = _parse_amount(m.group(1))
            continue

        amount_text = _cell(row, amount_col)
        # Some payslips merge AMOUNT and THIS YEAR into one cell as "X\nY"
        if this_year_col == amount_col and "\n" in amount_text:
            parts = amount_text.split("\n", 1)
            amount = _parse_amount(parts[0])
            this_year = _parse_amount(parts[1]) if len(parts) > 1 else None
        else:
            amount = _parse_amount(amount_text)
            this_year = (
                _parse_amount(_cell(row, this_year_col))
                if this_year_col is not None and this_year_col != amount_col
                else None
            )

        if amount is None:
            continue

        # Rate / units: from whatever column comes after desc (col 1), before amount_col
        rate_units_text = ""
        for c in range(1, amount_col):
            val = _cell(row, c)
            if val:
                rate_units_text = val
                break

        rate: float | None = None
        units: str | None = None
        if rate_units_text:
            if "\n" in rate_units_text:
                parts = rate_units_text.split("\n", 1)
                rate = _parse_amount(parts[0])
                units = parts[1].strip() if len(parts) > 1 else None
            else:
                rate = _parse_amount(rate_units_text)

        line_items.append(
            {
                "description": desc,
                "rate": rate,
                "units": units,
                "amount": amount,
                "this_year_amount": this_year,
                "line_type": "earning" if not past_total else "deduction",
            }
        )

    gross_pay = sum(it["amount"] for it in line_items if it["line_type"] == "earning")
    total_deductions = sum(it["amount"] for it in line_items if it["line_type"] == "deduction")

    return {
        "date": pay_date,
        "employer": employer,
        "ni_number": ni_number,
        "line_items": line_items,
        "net_pay": net_pay,
        "gross_pay": gross_pay,
        "total_deductions": total_deductions,
        "taxable_to_date": taxable_to_date,
    }
