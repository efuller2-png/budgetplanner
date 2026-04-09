import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "spending_tracker.db"

CATEGORIES = [
    "Groceries", "Dining", "Transport", "Health",
    "Entertainment", "Shopping", "Utilities", "Other"
]
PAYMENT_METHODS = ["Bank Card", "Credit Card", "Cash", "Other"]
ACCOUNT_TYPES   = ["Checking", "Savings", "Credit Card", "Other"]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Transactions ──────────────────────────────────────────────────────────────

def get_all_transactions() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql(
            "SELECT * FROM transactions ORDER BY date DESC;",
            conn
        )


def get_transactions_by_month(year: int, month: int) -> pd.DataFrame:
    m = f"{year}-{month:02d}"
    with get_conn() as conn:
        return pd.read_sql(
            """
            SELECT * 
            FROM transactions 
            WHERE strftime('%Y-%m', date) = ?
            ORDER BY date DESC;
            """,
            conn,
            params=(m,)
        )


def get_monthly_summary() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql("""
            SELECT
                strftime('%Y-%m', date) AS month,
                COUNT(*) AS transactions,
                ROUND(SUM(amount),2) AS total_spent
            FROM transactions
            GROUP BY month
            ORDER BY month;
        """, conn)


def get_weekly_summary(year: int, month: int) -> pd.DataFrame:
    m = f"{year}-{month:02d}"
    with get_conn() as conn:
        return pd.read_sql("""
            SELECT
                week_id,
                COUNT(*) AS transactions,
                ROUND(SUM(amount),2) AS total_spent
            FROM transactions
            WHERE strftime('%Y-%m', date) = ?
            GROUP BY week_id
            ORDER BY week_id;
        """, conn, params=(m,))


def get_category_summary(year: int, month: int) -> pd.DataFrame:
    m = f"{year}-{month:02d}"
    with get_conn() as conn:
        return pd.read_sql("""
            SELECT
                category,
                COUNT(*) AS transactions,
                ROUND(SUM(amount),2) AS total_spent
            FROM transactions
            WHERE strftime('%Y-%m', date) = ?
            GROUP BY category
            ORDER BY total_spent DESC;
        """, conn, params=(m,))


def insert_transaction(date, amount, category, payment_method,
                       merchant_city="", merchant_state="",
                       account_id="", note="") -> bool:
    parsed  = datetime.strptime(date, "%Y-%m-%d")
    week_id = parsed.strftime("%Y-W%V")
    try:
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO transactions
                    (date, amount, merchant_city, merchant_state,
                     category, payment_method, account_id,
                     entry_source, week_id, note)
                VALUES (?,?,?,?,?,?,?,'manual',?,?);
            """, (date, amount, merchant_city, merchant_state,
                  category, payment_method, account_id, week_id, note))
            conn.commit()
        return True
    except Exception as e:
        print(f"insert_transaction error: {e}")
        return False


# ── Budgets ───────────────────────────────────────────────────────────────────

def get_budget_vs_actual(week_id: str) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql("""
            SELECT
                b.category,
                b.weekly_limit,
                ROUND(COALESCE(SUM(t.amount),0),2) AS total_spent,
                ROUND(b.weekly_limit - COALESCE(SUM(t.amount),0),2) AS remaining,
                CASE 
                    WHEN COALESCE(SUM(t.amount),0) > b.weekly_limit THEN 1 
                    ELSE 0 
                END AS over_budget
            FROM budgets b
            LEFT JOIN transactions t
                ON t.category = b.category AND t.week_id = b.week_id
            WHERE b.week_id = ?
            GROUP BY b.category, b.weekly_limit
            ORDER BY total_spent DESC;
        """, conn, params=(week_id,))


def get_all_budget_weeks() -> list:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT week_id FROM budgets ORDER BY week_id DESC;")
        return [r[0] for r in cur.fetchall()]


def upsert_budget(category: str, weekly_limit: float, week_id: str) -> bool:
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM budgets WHERE category=? AND week_id=?;",
                (category, week_id)
            )
            row = cur.fetchone()

            if row:
                conn.execute(
                    "UPDATE budgets SET weekly_limit=? WHERE category=? AND week_id=?;",
                    (weekly_limit, category, week_id)
                )
            else:
                conn.execute(
                    "INSERT INTO budgets (category, weekly_limit, week_id) VALUES (?,?,?);",
                    (category, weekly_limit, week_id)
                )

            conn.commit()
        return True
    except Exception as e:
        print(f"upsert_budget error: {e}")
        return False


# ── Accounts ──────────────────────────────────────────────────────────────────

def get_all_accounts() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql(
            "SELECT * FROM accounts ORDER BY account_name;",
            conn
        )


def get_account_names() -> list:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT account_name FROM accounts ORDER BY account_name;")
        return [r[0] for r in cur.fetchall()]


def insert_account(account_name: str, account_type: str, bank_name: str = "") -> bool:
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO accounts (account_name, account_type, bank_name) VALUES (?,?,?);",
                (account_name, account_type, bank_name)
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"insert_account error: {e}")
        return False


def delete_account(account_id: int) -> bool:
    try:
        with get_conn() as conn:
            conn.execute("DELETE FROM accounts WHERE id=?;", (account_id,))
            conn.commit()
        return True
    except Exception as e:
        print(f"delete_account error: {e}")
        return False
