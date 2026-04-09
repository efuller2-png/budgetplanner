import streamlit as st
from datetime import date
import database as db

st.set_page_config(page_title="Log Cash", page_icon="💵", layout="centered")
st.title("💵 Log a Cash Purchase")
st.caption("Manually record any cash transaction so it shows in your spending.")

# ── Load accounts ─────────────────────────────────────────────
accounts_df = db.get_all_accounts()
account_options = ["— none —"] + accounts_df["account_name"].tolist()

with st.form("cash_form", clear_on_submit=True):
    amount = st.number_input("Amount ($)", min_value=0.01, step=0.01, format="%.2f")
    category = st.selectbox("Category", db.CATEGORIES)
    txn_date = st.date_input("Date", value=date.today(), max_value=date.today())
    merchant_city = st.text_input("City", placeholder="e.g. Spokane")
    merchant_state = st.text_input("State", placeholder="e.g. WA", max_chars=2)
    account_name = st.selectbox("Account (optional)", account_options)
    note = st.text_area("Note (optional)", placeholder="What was this for?")
    submitted = st.form_submit_button("Save transaction")

if submitted:
    # ── Validate inputs ─────────────────────────────
    errors = []
    if amount <= 0:
        errors.append("Amount must be greater than $0.00.")
    if not category:
        errors.append("Please select a category.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        # ── Prepare account ID ───────────────────
        if account_name == "— none —":
            account_id = ""
        else:
            # Map selected account name to ID
            matching = accounts_df.loc[accounts_df["account_name"] == account_name, "id"]
            account_id = str(matching.values[0]) if not matching.empty else ""

        # ── Clean state input ───────────────────
        merchant_state_clean = merchant_state.strip().upper()

        # ── Insert transaction ─────────────────
        success = db.insert_transaction(
            date=txn_date.strftime("%Y-%m-%d"),
            amount=round(amount, 2),
            category=category,
            payment_method="Cash",
            merchant_city=merchant_city.strip(),
            merchant_state=merchant_state_clean,
            account_id=account_id,
            note=note.strip()
        )

        if success:
            st.success(f"✅ ${round(amount,2):,.2f} in {category} saved successfully!")
        else:
            st.error("Something went wrong saving the transaction. Please try again.")
