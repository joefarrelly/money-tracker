"""Seed realistic demo data for the demo@montrack.app user."""

from datetime import date

from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    Account,
    Category,
    PayslipLineItem,
    PersonIdentity,
    RecurringExpense,
    Salary,
    Transaction,
    UserParserTemplate,
)

DEMO_USER = "demo@montrack.app"
DEMO_NI = "AA123456A"


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        if db.query(Account).filter_by(user_email=DEMO_USER).first():
            return
        _seed(db)
    finally:
        db.close()


def _seed(db: Session) -> None:
    cats = {c.name: c for c in db.query(Category).all()}

    current = Account(
        bank="Barclays", account_number="****1234", nickname="Barclays Current"
    )
    savings = Account(
        bank="Barclays", account_number="****5678", nickname="Barclays Savings"
    )
    chase = Account(bank="Chase", account_number="****9012", nickname="Chase")
    for a in (current, savings, chase):
        db.add(a)
    db.flush()

    # (date, description, amount, account, category_name, is_transfer)
    rows = [
        # January 2026
        ("2026-01-03", "TESCO SUPERSTORE", -78.34, current, "Groceries", False),
        ("2026-01-05", "COUNCIL TAX", -180.00, current, "Housing", False),
        ("2026-01-06", "SKY BROADBAND", -40.00, current, "Utilities", False),
        ("2026-01-07", "NETFLIX.COM", -17.99, current, "Subscriptions", False),
        ("2026-01-07", "SPOTIFY UK", -11.99, current, "Subscriptions", False),
        ("2026-01-10", "PURE GYM", -45.00, current, "Health", False),
        ("2026-01-10", "AVIVA CAR INSURANCE", -89.00, current, "Other", False),
        ("2026-01-11", "RENT - ANDERSON LETTING", -1200.00, current, "Housing", False),
        ("2026-01-14", "SAINSBURY'S LOCAL", -45.21, current, "Groceries", False),
        ("2026-01-15", "SALARY TECH CORP LTD", 3200.00, current, "Income", False),
        ("2026-01-17", "WAGAMAMA", -34.50, chase, "Eating Out", False),
        ("2026-01-18", "TFL TRAVEL", -28.50, current, "Transport", False),
        ("2026-01-19", "AMAZON.CO.UK", -67.99, chase, "Other", False),
        ("2026-01-21", "TESCO SUPERSTORE", -82.45, current, "Groceries", False),
        ("2026-01-24", "NANDOS", -28.75, chase, "Eating Out", False),
        ("2026-01-26", "DELIVEROO", -22.40, chase, "Eating Out", False),
        ("2026-01-28", "TESCO SUPERSTORE", -64.13, current, "Groceries", False),
        ("2026-01-29", "TRAINLINE", -42.80, current, "Transport", False),
        # February 2026
        ("2026-02-03", "COUNCIL TAX", -180.00, current, "Housing", False),
        ("2026-02-04", "SKY BROADBAND", -40.00, current, "Utilities", False),
        ("2026-02-05", "RENT - ANDERSON LETTING", -1200.00, current, "Housing", False),
        ("2026-02-07", "NETFLIX.COM", -17.99, current, "Subscriptions", False),
        ("2026-02-07", "SPOTIFY UK", -11.99, current, "Subscriptions", False),
        ("2026-02-07", "WAITROSE", -92.11, current, "Groceries", False),
        ("2026-02-10", "PURE GYM", -45.00, current, "Health", False),
        ("2026-02-10", "AVIVA CAR INSURANCE", -89.00, current, "Other", False),
        ("2026-02-14", "STARBUCKS", -8.60, chase, "Eating Out", False),
        ("2026-02-14", "COTE BRASSERIE", -68.40, chase, "Eating Out", False),
        ("2026-02-15", "SALARY TECH CORP LTD", 3200.00, current, "Income", False),
        ("2026-02-17", "SAINSBURY'S LOCAL", -51.30, current, "Groceries", False),
        ("2026-02-19", "TFL TRAVEL", -32.00, current, "Transport", False),
        ("2026-02-21", "AMAZON.CO.UK", -24.99, chase, "Other", False),
        ("2026-02-24", "TESCO SUPERSTORE", -71.55, current, "Groceries", False),
        ("2026-02-26", "DELIVEROO", -19.95, chase, "Eating Out", False),
        # March 2026
        ("2026-03-03", "COUNCIL TAX", -180.00, current, "Housing", False),
        ("2026-03-04", "SKY BROADBAND", -40.00, current, "Utilities", False),
        ("2026-03-05", "RENT - ANDERSON LETTING", -1200.00, current, "Housing", False),
        ("2026-03-07", "NETFLIX.COM", -17.99, current, "Subscriptions", False),
        ("2026-03-07", "SPOTIFY UK", -11.99, current, "Subscriptions", False),
        ("2026-03-10", "PURE GYM", -45.00, current, "Health", False),
        ("2026-03-10", "AVIVA CAR INSURANCE", -89.00, current, "Other", False),
        ("2026-03-12", "TESCO SUPERSTORE", -86.22, current, "Groceries", False),
        ("2026-03-15", "SALARY TECH CORP LTD", 3200.00, current, "Income", False),
        ("2026-03-16", "WAHACA", -31.20, chase, "Eating Out", False),
        ("2026-03-18", "TFL TRAVEL", -29.00, current, "Transport", False),
        ("2026-03-19", "MARKS AND SPENCER FOOD", -55.80, current, "Groceries", False),
        ("2026-03-20", "ASOS.COM", -87.50, chase, "Other", False),
        ("2026-03-22", "NANDOS", -27.90, chase, "Eating Out", False),
        ("2026-03-26", "TESCO SUPERSTORE", -68.70, current, "Groceries", False),
        ("2026-03-28", "DELIVEROO", -26.45, chase, "Eating Out", False),
        ("2026-03-30", "TRAINLINE", -38.00, current, "Transport", False),
        # April 2026
        ("2026-04-03", "COUNCIL TAX", -180.00, current, "Housing", False),
        ("2026-04-04", "SKY BROADBAND", -40.00, current, "Utilities", False),
        ("2026-04-05", "RENT - ANDERSON LETTING", -1200.00, current, "Housing", False),
        ("2026-04-07", "NETFLIX.COM", -17.99, current, "Subscriptions", False),
        ("2026-04-07", "SPOTIFY UK", -11.99, current, "Subscriptions", False),
        ("2026-04-10", "PURE GYM", -45.00, current, "Health", False),
        ("2026-04-10", "AVIVA CAR INSURANCE", -89.00, current, "Other", False),
        ("2026-04-11", "TESCO SUPERSTORE", -74.33, current, "Groceries", False),
        ("2026-04-15", "SALARY TECH CORP LTD", 3200.00, current, "Income", False),
        ("2026-04-16", "DISHOOM", -72.60, chase, "Eating Out", False),
        ("2026-04-17", "TFL TRAVEL", -26.50, current, "Transport", False),
        ("2026-04-19", "AMAZON.CO.UK", -112.49, chase, "Other", False),
        ("2026-04-21", "SAINSBURY'S LOCAL", -48.65, current, "Groceries", False),
        ("2026-04-24", "COSTA COFFEE", -7.40, chase, "Eating Out", False),
        ("2026-04-25", "TESCO SUPERSTORE", -79.12, current, "Groceries", False),
        ("2026-04-28", "DELIVEROO", -21.30, chase, "Eating Out", False),
        # May 2026
        ("2026-05-03", "COUNCIL TAX", -180.00, current, "Housing", False),
        ("2026-05-04", "SKY BROADBAND", -40.00, current, "Utilities", False),
        ("2026-05-05", "RENT - ANDERSON LETTING", -1200.00, current, "Housing", False),
        ("2026-05-07", "NETFLIX.COM", -17.99, current, "Subscriptions", False),
        ("2026-05-07", "SPOTIFY UK", -11.99, current, "Subscriptions", False),
        ("2026-05-10", "PURE GYM", -45.00, current, "Health", False),
        ("2026-05-10", "AVIVA CAR INSURANCE", -89.00, current, "Other", False),
        ("2026-05-12", "WAITROSE", -88.44, current, "Groceries", False),
        ("2026-05-15", "SALARY TECH CORP LTD", 3200.00, current, "Income", False),
        ("2026-05-16", "WAGAMAMA", -38.20, chase, "Eating Out", False),
        ("2026-05-18", "TFL TRAVEL", -31.50, current, "Transport", False),
        ("2026-05-20", "ZARA", -95.00, chase, "Other", False),
        ("2026-05-21", "TESCO SUPERSTORE", -72.80, current, "Groceries", False),
        ("2026-05-24", "BILLS BAR AND BRASSERIE", -44.80, chase, "Eating Out", False),
        ("2026-05-26", "SAINSBURY'S LOCAL", -53.20, current, "Groceries", False),
        ("2026-05-28", "DELIVEROO", -24.75, chase, "Eating Out", False),
        ("2026-05-31", "TRAINLINE", -55.00, current, "Transport", False),
        # June 2026 (partial)
        ("2026-06-03", "COUNCIL TAX", -180.00, current, "Housing", False),
        ("2026-06-04", "SKY BROADBAND", -40.00, current, "Utilities", False),
        ("2026-06-05", "RENT - ANDERSON LETTING", -1200.00, current, "Housing", False),
        ("2026-06-07", "NETFLIX.COM", -17.99, current, "Subscriptions", False),
        ("2026-06-07", "SPOTIFY UK", -11.99, current, "Subscriptions", False),
        ("2026-06-10", "PURE GYM", -45.00, current, "Health", False),
        ("2026-06-10", "AVIVA CAR INSURANCE", -89.00, current, "Other", False),
        ("2026-06-11", "TESCO SUPERSTORE", -76.22, current, "Groceries", False),
        ("2026-06-13", "TFL TRAVEL", -18.50, current, "Transport", False),
        ("2026-06-14", "SALARY TECH CORP LTD", 3200.00, current, "Income", False),
    ]

    # Savings transfers (separate list so we can link counterparts)
    transfer_months = [
        ("2026-01-01", "2026-01-01"),
        ("2026-02-01", "2026-02-01"),
        ("2026-03-01", "2026-03-01"),
        ("2026-04-01", "2026-04-01"),
        ("2026-05-01", "2026-05-01"),
        ("2026-06-01", "2026-06-01"),
    ]

    txns: list[Transaction] = []
    for date_str, desc, amount, acct, cat_name, is_transfer in rows:
        cat = cats.get(cat_name) if cat_name else None
        t = Transaction(
            account_id=acct.id,
            date=date.fromisoformat(date_str),
            description=desc,
            amount=amount,
            category_id=cat.id if cat else None,
            is_transfer=is_transfer,
        )
        db.add(t)
        txns.append(t)

    # Savings interest
    for month_n, interest, interest_date in [
        (1, 9.45, "2026-01-25"),
        (2, 9.82, "2026-02-22"),
        (3, 10.14, "2026-03-22"),
        (4, 10.67, "2026-04-22"),
        (5, 11.03, "2026-05-22"),
    ]:
        t = Transaction(
            account_id=savings.id,
            date=date.fromisoformat(interest_date),
            description="BARCLAYS SAVINGS INTEREST",
            amount=interest,
            category_id=cats.get("Income", cats.get("Other")).id if cats else None,
        )
        db.add(t)

    db.flush()

    # Linked transfer pairs
    for out_date, in_date in transfer_months:
        txn_out = Transaction(
            account_id=current.id,
            date=date.fromisoformat(out_date),
            description="TRANSFER TO SAVINGS",
            amount=-500.00,
            is_transfer=True,
        )
        txn_in = Transaction(
            account_id=savings.id,
            date=date.fromisoformat(in_date),
            description="TRANSFER FROM CURRENT",
            amount=500.00,
            is_transfer=True,
        )
        db.add(txn_out)
        db.add(txn_in)
        db.flush()
        txn_out.transfer_counterpart_id = txn_in.id
        txn_in.transfer_counterpart_id = txn_out.id

    # Recurring expenses
    recurring = [
        ("ANDERSON LETTING", 1200.00, "monthly", 5, "Housing"),
        ("COUNCIL TAX", 180.00, "monthly", 3, "Housing"),
        ("SKY BROADBAND", 40.00, "monthly", 4, "Utilities"),
        ("NETFLIX", 17.99, "monthly", 7, "Subscriptions"),
        ("SPOTIFY", 11.99, "monthly", 7, "Subscriptions"),
        ("PURE GYM", 45.00, "monthly", 10, "Health"),
        ("AVIVA", 89.00, "monthly", 10, "Other"),
    ]
    for pattern, amount, freq, dom, cat_name in recurring:
        db.add(
            RecurringExpense(
                merchant_pattern=pattern,
                typical_amount=amount,
                frequency=freq,
                day_of_month=dom,
                is_active=True,
                is_confirmed=True,
                category_id=cats.get(cat_name).id if cats.get(cat_name) else None,
            )
        )

    # Salaries + payslip line items (Jan–Jun 2026)
    salary_months = [
        (date(2026, 1, 15), 1),
        (date(2026, 2, 15), 2),
        (date(2026, 3, 15), 3),
        (date(2026, 4, 15), 4),
        (date(2026, 5, 15), 5),
        (date(2026, 6, 14), 6),
    ]
    for pay_date, month_num in salary_months:
        sal = Salary(
            date=pay_date,
            gross_amount=4600.00,
            net_amount=3200.00,
            employer="Tech Corp Ltd",
            ni_number=DEMO_NI,
            source_file="demo_payslip.pdf",
        )
        db.add(sal)
        db.flush()

        line_items = [
            ("Basic Salary", 4600.00, "earning", 4600.00 * month_num),
            ("Income Tax", -780.00, "deduction", 780.00 * month_num),
            ("National Insurance", -391.00, "deduction", 391.00 * month_num),
            ("Pension (Employee)", -229.00, "deduction", 229.00 * month_num),
        ]
        for desc, amt, line_type, ytd in line_items:
            db.add(
                PayslipLineItem(
                    salary_id=sal.id,
                    description=desc,
                    amount=amt,
                    line_type=line_type,
                    this_year_amount=round(ytd, 2),
                )
            )

    # Person identity
    db.add(PersonIdentity(ni_number=DEMO_NI, display_name="Demo User"))

    # Parser templates (illustrative — not functional without real files)
    db.add(
        UserParserTemplate(
            user_email=DEMO_USER,
            name="Barclays CSV",
            template_type="statement",
            file_type="csv",
            table_index=0,
            amount_style="split",
            date_col=0,
            description_col=1,
            money_in_col=2,
            money_out_col=3,
            balance_col=4,
            date_format="%d/%m/%Y",
            year_source="inline",
            skip_patterns=["Opening Balance"],
        )
    )
    db.add(
        UserParserTemplate(
            user_email=DEMO_USER,
            name="Tech Corp Payslip",
            template_type="payslip",
            file_type="pdf",
            table_index=0,
            amount_style="signed",
            description_col=0,
            amount_col=3,
            deduction_boundary_keyword="TOTAL",
            skip_patterns=["Ers NIC*", "Ers Pension*", "NET PAY"],
        )
    )

    db.commit()
