import streamlit as st
import database as db

st.set_page_config(page_title="Account Manager", page_icon="🏦", layout="centered")

st.title("🏦 Account Manager")
st.caption("Add and manage your linked bank and card accounts.")

# ── Existing accounts ─────────────────────────────────────────────────────────
st.subheader("Your accounts")
df = db.get_all_accounts()

if df.empty:
    st.info("No accounts added yet. Add one below.")
else:
    for _, row in df.iterrows():
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        col1.markdown(f"**{row['account_name']}**")
        col2.markdown(row["account_type"])
        col3.markdown(row["bank_name"] if row["bank_name"] else "—")
        
        # Remove button
        if col4.button("Remove", key=f"del_{row['id']}"):
            ok = db.delete_account(int(row["id"]))
            if ok:
                st.success(f"✅ Removed {row['account_name']}.")
                st.experimental_rerun()  # Streamlit-safe rerun
            else:
                st.error("Could not remove account.")

st.divider()

# ── Add new account ───────────────────────────────────────────────────────────
st.subheader("Add a new account")

with st.form("account_form", clear_on_submit=True):
    account_name = st.text_input("Account name", placeholder="e.g. Main Checking")
    account_type = st.selectbox("Account type", db.ACCOUNT_TYPES)
    bank_name    = st.text_input("Bank name", placeholder="e.g. Chase")
    submitted    = st.form_submit_button("Add account")

if submitted:
    account_name_clean = account_name.strip()
    bank_name_clean    = bank_name.strip()
    
    if not account_name_clean:
        st.error("Account name is required.")
    else:
        ok = db.insert_account(account_name_clean, account_type, bank_name_clean)
        if ok:
            st.success(f"✅ {account_name_clean} added successfully!")
            st.experimental_rerun()
        else:
            st.error("Could not add account. Please try again.")
