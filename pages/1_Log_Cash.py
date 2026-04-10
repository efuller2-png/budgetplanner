import streamlit as st
import pandas as pd
from datetime import date
import database as db

st.set_page_config(page_title="Log Cash", page_icon="💵", layout="wide")
st.title("💵 Cash Transactions")
st.caption("Log cash purchases and manage all your transactions.")

tab1, tab2 = st.tabs(["Log a cash purchase", "View & manage transactions"])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — Log new cash purchase
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    with st.form("cash_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        amount         = col1.number_input("Amount ($) *", min_value=0.01, step=0.01, format="%.2f")
        category       = col2.selectbox("Category *", db.CATEGORIES)
        txn_date       = col1.date_input("Date *", value=date.today(), max_value=date.today())
        payment_method = col2.selectbox("Payment method *", db.PAYMENT_METHODS)
        merchant_city  = col1.text_input("City", placeholder="e.g. Spokane")
        merchant_state = col2.text_input("State", placeholder="e.g. WA", max_chars=2)

        accounts   = db.get_account_names()
        account_id = st.selectbox("Account (optional)", ["— none —"] + accounts)

        tag_names     = db.get_tag_names()
        selected_tags = st.multiselect("Tags (optional)", tag_names)

        note      = st.text_area("Note (optional)", placeholder="What was this for?")
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
                date=txn_date.strftime("%Y-%m-%d"), amount=round(amount, 2),
                category=category, payment_method=payment_method,
                merchant_city=merchant_city, merchant_state=merchant_state.upper(),
                account_id=acc, note=note,
            )
            if ok:
                st.success(f"✅ ${amount:,.2f} in {category} saved!")
            else:
                st.error("Something went wrong. Please try again.")

    st.divider()
    st.subheader("Manage tags")
    st.caption("Tags are shared across all transactions.")
    col_a, col_b = st.columns([3, 1])
    new_tag = col_a.text_input("New tag name", placeholder="e.g. road trip")
    if col_b.button("Add tag", use_container_width=True):
        if new_tag.strip():
            db.insert_tag(new_tag.strip())
            st.success(f"Tag '{new_tag}' added!")
            st.rerun()
        else:
            st.error("Tag name cannot be empty.")

    tags_df = db.get_all_tags()
    if not tags_df.empty:
        st.markdown("**Existing tags:**")
        for _, row in tags_df.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.markdown(row["name"])
            if c2.button("Remove", key=f"deltag_{row['id']}"):
                db.delete_tag(int(row["id"]))
                st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — View, search, edit, delete
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Search & filter")
    col1, col2 = st.columns(2)
    search_term = col1.text_input("Search by city or note", placeholder="e.g. Spokane")
    filter_cat  = col2.selectbox("Filter by category", ["All"] + db.CATEGORIES)

    cat_filter = "" if filter_cat == "All" else filter_cat
    df = db.search_transactions(search_term=search_term, category=cat_filter)

    if df.empty:
        st.info("No transactions found.")
    else:
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

        st.markdown(f"**{len(df)} transactions found**")
        for _, row in df.iterrows():
            amount_val = float(row["amount"]) if pd.notna(row["amount"]) else 0.0
            with st.expander(f"{row['date']} — {row['category']} — ${amount_val:,.2f}"):
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**City:** {row['merchant_city'] or '—'}")
                col2.markdown(f"**State:** {row['merchant_state'] or '—'}")
                col3.markdown(f"**Payment:** {row['payment_method']}")
                st.markdown(f"**Note:** {row['note'] or '—'}")
                st.markdown("---")
                edit_col, del_col = st.columns(2)

                with edit_col:
                    with st.form(f"edit_{row['id']}"):
                        st.markdown("**Edit transaction**")
                        new_amount = st.number_input(
                            "Amount ($)", value=amount_val,
                            min_value=0.01, step=0.01, format="%.2f",
                            key=f"amt_{row['id']}"
                        )
                        new_cat = st.selectbox(
                            "Category", db.CATEGORIES,
                            index=db.CATEGORIES.index(row["category"])
                            if row["category"] in db.CATEGORIES else 0,
                            key=f"cat_{row['id']}"
                        )
                        new_payment = st.selectbox(
                            "Payment method", db.PAYMENT_METHODS,
                            index=db.PAYMENT_METHODS.index(row["payment_method"])
                            if row["payment_method"] in db.PAYMENT_METHODS else 0,
                            key=f"pay_{row['id']}"
                        )
                        new_city = st.text_input(
                            "City", value=row["merchant_city"] or "",
                            key=f"city_{row['id']}"
                        )
                        new_note = st.text_area(
                            "Note", value=row["note"] or "",
                            key=f"note_{row['id']}"
                        )
                        if st.form_submit_button("Save changes"):
                            if new_amount <= 0:
                                st.error("Amount must be greater than $0.")
                            else:
                                ok = db.update_transaction(
                                    transaction_id=int(row["id"]),
                                    date=str(row["date"]),
                                    amount=round(new_amount, 2),
                                    category=new_cat,
                                    payment_method=new_payment,
                                    merchant_city=new_city,
                                    merchant_state=str(row["merchant_state"] or ""),
                                    note=new_note,
                                )
                                if ok:
                                    st.success("Updated!")
                                    st.rerun()
                                else:
                                    st.error("Update failed.")

                with del_col:
                    st.markdown("**Delete transaction**")
                    st.warning("This cannot be undone.")
                    confirm = st.checkbox(
                        "I confirm I want to delete this",
                        key=f"confirm_{row['id']}"
                    )
                    if st.button(
                        "Delete", key=f"del_{row['id']}",
                        type="primary", disabled=not confirm
                    ):
                        ok = db.delete_transaction(int(row["id"]))
                        if ok:
                            st.success("Deleted.")
                            st.rerun()
                        else:
                            st.error("Delete failed.")