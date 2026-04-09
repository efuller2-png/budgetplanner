cat > README.md << 'READMEEOF'
# Personal Spending Tracker

A Streamlit web application backed by a PostgreSQL database that tracks personal spending on a day-to-day basis. Users can log cash purchases manually, view month-to-month and weekly spending breakdowns, set weekly budget limits per category, and manage linked bank accounts. Transactions can be labeled with tags for custom filtering and organization.

**Live App:** [https://budgetplanner-x5ravdkh6dg4ns695amwlx.streamlit.app](https://budgetplanner-x5ravdkh6dg4ns695amwlx.streamlit.app)

---

## ERD (Entity-Relationship Diagram)

![ERD](erd.png)

---

## Table Descriptions

### transactions
The central table of the system. Stores every purchase — either auto-synced from a bank account or manually logged as a cash entry. Tracks the date, amount, category, payment method, merchant location, and which week the transaction belongs to for budget rollup purposes.

### budgets
Stores weekly spending limits per category. Each row represents one category's limit for one specific week (e.g. $150 for Groceries in week 2026-W14). The UNIQUE(category, week_id) constraint prevents duplicate budget entries.

### accounts
Stores the user's linked bank and card accounts. Each account has a name, type (Checking, Savings, Credit Card, Other), and bank name. Transactions reference accounts by name so the user can track which account was used for each purchase.

### tags
A shared library of custom labels the user creates (e.g. "road trip", "work lunch", "subscription"). Tags are reusable across any number of transactions.

### transaction_tags
The junction table that implements the many-to-many relationship between transactions and tags. One transaction can have many tags, and one tag can apply to many transactions. Deleting a transaction automatically removes its tag links via ON DELETE CASCADE.

---

## How to Run Locally

### Prerequisites
- Python 3.10+
- A PostgreSQL database (e.g. Supabase free tier)

### 1. Clone the repository
git clone https://github.com/efuller2-png/budgetplanner.git
cd budgetplanner

### 2. Install dependencies
pip install -r requirements.txt

### 3. Set up secrets
Create a file at .streamlit/secrets.toml with your database connection string:
DB_URL = "postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres"

Never commit this file to GitHub. It is already listed in .gitignore.

### 4. Run the app
streamlit run app.py

The app will automatically create all database tables on first run if they do not exist.

---

## Pages

| Page | Description |
|------|-------------|
| Home | Month-to-month spending metrics, weekly breakdown, and category breakdown charts |
| Log Cash | Form to manually log cash purchases; view, search, edit, and delete all transactions |
| Budget Manager | Set weekly spending limits per category with progress bar tracking |
| Account Manager | Add, edit, and remove linked bank and card accounts |

---

## Project Info

- Built with: Streamlit, PostgreSQL (Supabase), psycopg2, Plotly, pandas
- Deployed on: Streamlit Community Cloud
- Course: BMIS 444
READMEEOF