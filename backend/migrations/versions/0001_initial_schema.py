"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-14

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("bank", sa.String(50), nullable=False),
        sa.Column("account_number", sa.String(50), nullable=False),
        sa.Column("nickname", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_accounts_user_email",
        "accounts",
        ["user_email"],
        unique=False,
        if_not_exists=True,
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        if_not_exists=True,
    )

    op.create_table(
        "person_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("ni_number", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_person_identities_user_email",
        "person_identities",
        ["user_email"],
        unique=False,
        if_not_exists=True,
    )

    op.create_table(
        "recurring_expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("merchant_pattern", sa.String(255), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("typical_amount", sa.Float(), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_recurring_expenses_user_email",
        "recurring_expenses",
        ["user_email"],
        unique=False,
        if_not_exists=True,
    )

    op.create_table(
        "salaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("gross_amount", sa.Float(), nullable=True),
        sa.Column("net_amount", sa.Float(), nullable=False),
        sa.Column("employer", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("ni_number", sa.String(20), nullable=True),
        sa.Column("source_file", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_salaries_user_email",
        "salaries",
        ["user_email"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "idx_salary_date_ni",
        "salaries",
        ["date", "ni_number"],
        unique=True,
        postgresql_where=sa.text("ni_number IS NOT NULL"),
        if_not_exists=True,
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("balance", sa.Float(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("is_recurring", sa.Boolean(), nullable=True),
        sa.Column("is_transfer", sa.Boolean(), nullable=True),
        sa.Column("transfer_counterpart_id", sa.Integer(), nullable=True),
        sa.Column("transfer_ignored", sa.Boolean(), nullable=True),
        sa.Column("source_file", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["transfer_counterpart_id"], ["transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )

    op.create_table(
        "payslip_line_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("salary_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("rate", sa.Float(), nullable=True),
        sa.Column("units", sa.String(100), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("this_year_amount", sa.Float(), nullable=True),
        sa.Column("line_type", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(["salary_id"], ["salaries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )

    op.create_table(
        "email_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("message_id", sa.String(500), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("sender", sa.String(255), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("import_type", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_email_imports_user_email",
        "email_imports",
        ["user_email"],
        unique=False,
        if_not_exists=True,
    )

    op.create_table(
        "user_email_configs",
        sa.Column("user_email", sa.String(255), nullable=False),
        sa.Column("app_password", sa.String(255), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("user_email"),
        if_not_exists=True,
    )

    op.create_table(
        "user_parser_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("template_type", sa.String(20), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("table_index", sa.Integer(), nullable=True),
        sa.Column("column_headers", sa.JSON(), nullable=True),
        sa.Column("date_col", sa.Integer(), nullable=True),
        sa.Column("description_col", sa.Integer(), nullable=True),
        sa.Column("date_description_col", sa.Integer(), nullable=True),
        sa.Column("balance_col", sa.Integer(), nullable=True),
        sa.Column("amount_style", sa.String(10), nullable=False),
        sa.Column("amount_col", sa.Integer(), nullable=True),
        sa.Column("money_in_col", sa.Integer(), nullable=True),
        sa.Column("money_out_col", sa.Integer(), nullable=True),
        sa.Column("date_format", sa.String(30), nullable=True),
        sa.Column("year_source", sa.String(20), nullable=True),
        sa.Column("skip_patterns", sa.JSON(), nullable=False),
        sa.Column("deduction_boundary_keyword", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_user_parser_templates_user_email",
        "user_parser_templates",
        ["user_email"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("user_parser_templates")
    op.drop_table("user_email_configs")
    op.drop_table("email_imports")
    op.drop_table("payslip_line_items")
    op.drop_table("transactions")
    op.drop_table("salaries")
    op.drop_table("recurring_expenses")
    op.drop_table("person_identities")
    op.drop_table("categories")
    op.drop_table("accounts")
