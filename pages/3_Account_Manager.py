import streamlit as st
import database as db

st.set_page_config(page_title="Account Manager", page_icon="🏦", layout="centered")
st.title("🏦 Account Manager")
st.caption("Add and manage your linked bank and card accounts.")

st.subheader("Your accounts")
df = db.get_all_accounts()

if df.empty:
    st.info("No accounts added yet. Add one below.")
else:
    for idx, row in df.iterrows():
        with st.expander(f"{row['account_name']} — {row['account_type']} — {row['bank_name'] or '—'}"):
            col1, col2 = st.columns(2)

            with col1:
                with st.form(f"edit_acc_{idx}"):
                    st.markdown("**Edit account**")
                    new_name = st.text_input(
                        "Account name",
                        value=row["account_name"],
                        key=f"name_{idx}"
                    )
                    new_type = st.selectbox(
                        "Account type",
                        db.ACCOUNT_TYPES,
                        index=db.ACCOUNT_TYPES.index(row["account_type"])
                        if row["account_type"] in db.ACCOUNT_TYPES else 0,
                        key=f"type_{idx}"
                    )
                    new_bank = st.text_input(
                        "Bank name",
                        value=row["bank_name"] or "",
                        key=f"bank_{idx}"
                    )
                    if st.form_submit_button("Save changes"):
                        if not new_name.strip():
                            st.error("Account name is required.")
                        else:
                            ok = db.update_account(
                                int(row["id"]),
                                new_name.strip(),
                                new_type,
                                new_bank.strip()
                            )
                            if ok:
                                st.success("Account updated!")
                                st.rerun()
                            else:
                                st.error("Update failed.")

            with col2:
                st.markdown("**Delete account**")
                st.warning("This cannot be undone.")
                confirm = st.checkbox(
                    "I confirm I want to delete this account",
                    key=f"confirm_acc_{idx}"
                )
                if st.button(
                    "Delete account",
                    key=f"del_acc_{idx}",
                    type="primary",
                    disabled=not confirm
                ):
                    ok = db.delete_account(int(row["id"]))
                    if ok:
                        st.success(f"Removed {row['account_name']}.")
                        st.rerun()
                    else:
                        st.error("Could not remove account.")

st.divider()
st.subheader("Add a new account")

with st.form("account_form", clear_on_submit=True):
    account_name = st.text_input("Account name *", placeholder="e.g. Main Checking")
    account_type = st.selectbox("Account type *", db.ACCOUNT_TYPES)
    bank_name    = st.text_input("Bank name", placeholder="e.g. Chase")
    submitted    = st.form_submit_button("Add account")

if submitted:
    errors = []
    if not account_name.strip():
        errors.append("Account name is required.")
    if errors:
        for e in errors:
            st.error(e)
    else:
        ok = db.insert_account(account_name.strip(), account_type, bank_name.strip())
        if ok:
            st.success(f"✅ {account_name} added successfully!")
            st.rerun()
        else:
            st.error("Could not add account. Please try again.")