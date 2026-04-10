import streamlit as st
import pandas as pd
import psycopg2

CATEGORIES = [
    "Groceries", "Dining", "Transport", "Health",
    "Entertainment", "Shopping", "Utilities", "Other"
]
PAYMENT_METHODS = ["Bank Card", "Credit Card", "Cash", "Other"]
ACCOUNT_TYPES   = ["Checking", "Savings", "Credit Card", "Other"]


def get_conn():
    return psycopg2.connect(st.secrets["DB_URL"])


def _safe_float(val):
    try:
        return float(val) if val is not None else 0.0
    except:
        return 0.0


def _fix(df, *cols):
    for col in cols:
        if col in df.columns:
            df[col] = df[col].apply(_safe_float)
    return df


def init_db():
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id           SERIAL PRIMARY KEY,
                account_name VARCHAR(255) NOT NULL,
                account_type VARCHAR(50)  NOT NULL,
                bank_name    VARCHAR(255),
                created_at   TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS budgets (
                id           SERIAL PRIMARY KEY,
                category     VARCHAR(100) NOT NULL,
                weekly_limit DECIMAL(10,2) NOT NULL,
                week_id      VARCHAR(10)  NOT NULL,
                UNIQUE (category, week_id),
                created_at   TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id                  SERIAL PRIMARY KEY,
                date                DATE          NOT NULL,
                amount              DECIMAL(10,2) NOT NULL CHECK (amount > 0),
                merchant_city       VARCHAR(100),
                merchant_state      CHAR(2),
                category            VARCHAR(100) NOT NULL,
                subcategory         VARCHAR(100),
                payment_method      VARCHAR(50)  NOT NULL,
                account_id          VARCHAR(100),
                entry_source        VARCHAR(20)  DEFAULT 'bank_sync',
                bank_transaction_id VARCHAR(255),
                week_id             VARCHAR(10),
                budget_category_id  INTEGER REFERENCES budgets(id),
                note                TEXT,
                receipt_image_url   VARCHAR(500),
                created_at          TIMESTAMP DEFAULT NOW(),
                updated_at          TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS tags (
                id   SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS transaction_tags (
                transaction_id INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
                tag_id         INTEGER REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (transaction_id, tag_id)
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"init_db error: {e}")


# ── Transactions — Read ───────────────────────────────────────────────────────

def get_transactions_by_month(year: int, month: int) -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("""
            SELECT * FROM transactions
            WHERE EXTRACT(YEAR  FROM date) = %s
            AND   EXTRACT(MONTH FROM date) = %s
            ORDER BY date DESC;
        """, conn, params=(year, month))
        conn.close()
        return _fix(df, "amount")
    except Exception as e:
        print(f"get_transactions_by_month error: {e}")
        return pd.DataFrame()


def get_all_transactions() -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("SELECT * FROM transactions ORDER BY date DESC;", conn)
        conn.close()
        return _fix(df, "amount")
    except Exception as e:
        print(f"get_all_transactions error: {e}")
        return pd.DataFrame()


def search_transactions(search_term: str = "", category: str = "") -> pd.DataFrame:
    try:
        query  = "SELECT * FROM transactions WHERE 1=1"
        params = []
        if search_term:
            query += " AND (merchant_city ILIKE %s OR note ILIKE %s)"
            params += [f"%{search_term}%", f"%{search_term}%"]
        if category:
            query += " AND category = %s"
            params.append(category)
        query += " ORDER BY date DESC;"
        conn = get_conn()
        df   = pd.read_sql(query, conn, params=params)
        conn.close()
        return _fix(df, "amount")
    except Exception as e:
        print(f"search_transactions error: {e}")
        return pd.DataFrame()


# ── Aggregates ────────────────────────────────────────────────────────────────

def get_monthly_summary() -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("""
            SELECT
                TO_CHAR(date, 'YYYY-MM')       AS month,
                COUNT(*)                       AS transactions,
                ROUND(SUM(amount)::numeric, 2) AS total_spent
            FROM transactions
            GROUP BY month ORDER BY month;
        """, conn)
        conn.close()
        return _fix(df, "total_spent")
    except Exception as e:
        print(f"get_monthly_summary error: {e}")
        return pd.DataFrame()


def get_weekly_summary(year: int, month: int) -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("""
            SELECT
                week_id,
                COUNT(*)                       AS transactions,
                ROUND(SUM(amount)::numeric, 2) AS total_spent
            FROM transactions
            WHERE EXTRACT(YEAR  FROM date) = %s
            AND   EXTRACT(MONTH FROM date) = %s
            GROUP BY week_id ORDER BY week_id;
        """, conn, params=(year, month))
        conn.close()
        return _fix(df, "total_spent")
    except Exception as e:
        print(f"get_weekly_summary error: {e}")
        return pd.DataFrame()


def get_category_summary(year: int, month: int) -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("""
            SELECT
                category,
                COUNT(*)                       AS transactions,
                ROUND(SUM(amount)::numeric, 2) AS total_spent
            FROM transactions
            WHERE EXTRACT(YEAR  FROM date) = %s
            AND   EXTRACT(MONTH FROM date) = %s
            GROUP BY category ORDER BY total_spent DESC;
        """, conn, params=(year, month))
        conn.close()
        return _fix(df, "total_spent")
    except Exception as e:
        print(f"get_category_summary error: {e}")
        return pd.DataFrame()


# ── Transactions — Write ──────────────────────────────────────────────────────

def insert_transaction(date, amount, category, payment_method,
                       merchant_city="", merchant_state="",
                       account_id="", note="") -> bool:
    from datetime import datetime as dt
    try:
        week_id = dt.strptime(str(date), "%Y-%m-%d").strftime("%Y-W%V")
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO transactions
                (date, amount, merchant_city, merchant_state, category,
                 payment_method, account_id, entry_source, week_id, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'manual', %s, %s);
        """, (date, amount, merchant_city, merchant_state, category,
              payment_method, account_id, week_id, note))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"insert_transaction error: {e}")
        return False


def update_transaction(transaction_id, date, amount, category,
                       payment_method, merchant_city="",
                       merchant_state="", note="") -> bool:
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute("""
            UPDATE transactions SET
                date=%s, amount=%s, category=%s, payment_method=%s,
                merchant_city=%s, merchant_state=%s, note=%s,
                updated_at=NOW()
            WHERE id=%s;
        """, (date, amount, category, payment_method,
              merchant_city, merchant_state, note, transaction_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"update_transaction error: {e}")
        return False


def delete_transaction(transaction_id) -> bool:
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute("DELETE FROM transactions WHERE id=%s;", (int(transaction_id),))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"delete_transaction error: {e}")
        return False


# ── Tags ──────────────────────────────────────────────────────────────────────

def get_all_tags() -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("SELECT * FROM tags ORDER BY name;", conn)
        conn.close()
        return df
    except Exception as e:
        print(f"get_all_tags error: {e}")
        return pd.DataFrame()


def get_tag_names() -> list:
    df = get_all_tags()
    return df["name"].tolist() if not df.empty else []


def insert_tag(name: str) -> bool:
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO tags (name) VALUES (%s) ON CONFLICT (name) DO NOTHING;",
            (name.strip(),)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"insert_tag error: {e}")
        return False


def delete_tag(tag_id) -> bool:
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute("DELETE FROM tags WHERE id=%s;", (int(tag_id),))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"delete_tag error: {e}")
        return False


def add_tag_to_transaction(transaction_id, tag_id) -> bool:
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO transaction_tags (transaction_id, tag_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING;
        """, (int(transaction_id), int(tag_id)))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"add_tag_to_transaction error: {e}")
        return False


def get_tags_for_transaction(transaction_id) -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("""
            SELECT t.id, t.name FROM tags t
            JOIN transaction_tags tt ON tt.tag_id = t.id
            WHERE tt.transaction_id = %s ORDER BY t.name;
        """, conn, params=(int(transaction_id),))
        conn.close()
        return df
    except Exception as e:
        print(f"get_tags_for_transaction error: {e}")
        return pd.DataFrame()


def get_transactions_by_tag(tag_name: str) -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("""
            SELECT tx.* FROM transactions tx
            JOIN transaction_tags tt ON tt.transaction_id = tx.id
            JOIN tags t ON t.id = tt.tag_id
            WHERE t.name = %s ORDER BY tx.date DESC;
        """, conn, params=(tag_name,))
        conn.close()
        return _fix(df, "amount")
    except Exception as e:
        print(f"get_transactions_by_tag error: {e}")
        return pd.DataFrame()


# ── Budgets ───────────────────────────────────────────────────────────────────

def get_budget_vs_actual(week_id: str) -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("""
            SELECT
                b.category,
                b.weekly_limit,
                ROUND(COALESCE(SUM(t.amount), 0)::numeric, 2)                    AS total_spent,
                ROUND((b.weekly_limit - COALESCE(SUM(t.amount), 0))::numeric, 2) AS remaining,
                CASE WHEN COALESCE(SUM(t.amount), 0) > b.weekly_limit
                     THEN true ELSE false END                                     AS over_budget
            FROM budgets b
            LEFT JOIN transactions t
                   ON t.category = b.category AND t.week_id = b.week_id
            WHERE b.week_id = %s
            GROUP BY b.category, b.weekly_limit
            ORDER BY total_spent DESC;
        """, conn, params=(week_id,))
        conn.close()
        return _fix(df, "weekly_limit", "total_spent", "remaining")
    except Exception as e:
        print(f"get_budget_vs_actual error: {e}")
        return pd.DataFrame()


def get_all_budget_weeks() -> list:
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute("SELECT DISTINCT week_id FROM budgets ORDER BY week_id DESC;")
        rows = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"get_all_budget_weeks error: {e}")
        return []


def upsert_budget(category: str, weekly_limit: float, week_id: str) -> bool:
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO budgets (category, weekly_limit, week_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (category, week_id)
            DO UPDATE SET weekly_limit = EXCLUDED.weekly_limit;
        """, (category, weekly_limit, week_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"upsert_budget error: {e}")
        return False


# ── Accounts ──────────────────────────────────────────────────────────────────

def get_all_accounts() -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("SELECT * FROM accounts ORDER BY account_name;", conn)
        conn.close()
        return df
    except Exception as e:
        print(f"get_all_accounts error: {e}")
        return pd.DataFrame()


def get_account_names() -> list:
    df = get_all_accounts()
    return df["account_name"].tolist() if not df.empty else []


def insert_account(account_name: str, account_type: str, bank_name: str = "") -> bool:
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO accounts (account_name, account_type, bank_name) VALUES (%s, %s, %s);",
            (account_name, account_type, bank_name)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"insert_account error: {e}")
        return False


def delete_account(account_id) -> bool:
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute("DELETE FROM accounts WHERE id=%s;", (int(account_id),))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"delete_account error: {e}")
        return False


def update_account(account_id, account_name: str, account_type: str, bank_name: str) -> bool:
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute("""
            UPDATE accounts SET
                account_name=%s, account_type=%s, bank_name=%s
            WHERE id=%s;
        """, (account_name, account_type, bank_name, int(account_id)))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"update_account error: {e}")
        return False