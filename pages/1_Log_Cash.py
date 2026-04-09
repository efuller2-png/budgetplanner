import streamlit as st
from datetime import date
import database as db

st.set_page_config(page_title="Log Cash", page_icon="💵", layout="centered")

st.title("💵 Log a Cash Purchase")
st.caption("Manually record any cash transaction so it shows in your spending.")

with st.form("cash_form", clear_on_submit=True):
    amount = st.number_input("Amount ($)", min_value=0.01, step=0.01, format="%.2f")

    category = st.selectbox("Category", db.CATEGORIES)

    txn_date = st.date_input("Date", value=date.today(), max_value=date.today())

    merchant_city  = st.text_input("City",  placeholder="e.g. Spokane")
    merchant_state = st.text_input("State", placeholder="e.g. WA", max_chars=2)

    accounts       = db.get_account_names()
    account_id     = st.selectbox("Account (optional)", ["— none —"] + accounts)

    note           = st.text_area("Note (optional)", placeholder="What was this for?")

    submitted = st.form_submit_button("Save transaction")

if submitted:
    errors = []
    if amount <= 0:
        errors.append("Amount must be greater than $0.00.")
    if not category:
        errors.append("Please select a category.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        acc = "" if account_id == "— none —" else account_id
        ok  = db.insert_transaction(
            date           = txn_date.strftime("%Y-%m-%d"),
            amount         = round(amount, 2),
            category       = category,
            payment_method = "Cash",
            merchant_city  = merchant_city,
            merchant_state = merchant_state.upper(),
            account_id     = acc,
            note           = note,
        )
        if ok:
            st.success(f"✅ ${amount:,.2f} in {category} saved successfully!")
        else:
            st.error("Something went wrong saving the transaction. Please try again.")