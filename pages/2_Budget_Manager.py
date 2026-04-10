import streamlit as st
from datetime import datetime, timedelta
import database as db
 
st.set_page_config(page_title="Budget Manager", page_icon="📊", layout="wide")
st.title("📊 Budget Manager")
st.caption("Set weekly spending limits per category and track your progress.")
 
today = datetime.today()
weeks = sorted(set(
    (today - timedelta(weeks=i)).strftime("%Y-W%V") for i in range(-1, 8)
), reverse=True)
 
week_id = st.selectbox("Select week", weeks)
st.divider()
 
# ── Set limits ────────────────────────────────────────────────────────────────
st.subheader("Set limits for this week")
 
existing  = db.get_budget_vs_actual(week_id)
limit_map = {}
if not existing.empty and "category" in existing.columns and "weekly_limit" in existing.columns:
    for _, row in existing.iterrows():
        try:
            limit_map[row["category"]] = float(str(row["weekly_limit"]))
        except:
            limit_map[row["category"]] = 0.0
 
with st.form("budget_form"):
    cols       = st.columns(2)
    new_limits = {}
    for i, cat in enumerate(db.CATEGORIES):
        current         = limit_map.get(cat, 0.0)
        new_limits[cat] = cols[i % 2].number_input(
            cat,
            min_value=0.0,
            value=float(current),
            step=5.0,
            format="%.2f",
            key=f"budget_{cat}"
        )
    save = st.form_submit_button("Save budgets")
 
if save:
    errors = []
    for cat, limit in new_limits.items():
        if limit < 0:
            errors.append(f"{cat} limit cannot be negative.")
    if errors:
        for e in errors:
            st.error(e)
    else:
        saved = 0
        for cat, limit in new_limits.items():
            if limit > 0:
                ok = db.upsert_budget(cat, limit, week_id)
                if ok:
                    saved += 1
        st.success(f"✅ {saved} budget limits saved for {week_id}.")
        st.rerun()
 
st.divider()
 
# ── Progress bars ─────────────────────────────────────────────────────────────
st.subheader("This week's progress")
 
df = db.get_budget_vs_actual(week_id)
 
if df.empty:
    st.info("No budgets set for this week yet. Add limits above to get started.")
else:
    for _, row in df.iterrows():
        try:
            cat       = row["category"]
            limit     = float(str(row["weekly_limit"])) if row["weekly_limit"] is not None else 0.0
            spent     = float(str(row["total_spent"]))  if row["total_spent"]  is not None else 0.0
            remaining = float(str(row["remaining"]))    if row["remaining"]    is not None else 0.0
            over      = bool(row["over_budget"])
            pct       = min(spent / limit, 1.0) if limit > 0 else 0.0
 
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.markdown(f"**{cat}**")
            col2.markdown(f"${spent:,.2f} / ${limit:,.2f}")
 
            if over:
                col3.markdown(f"🔴 **Over by ${abs(remaining):,.2f}**")
                st.progress(1.0)
                st.caption(f"⚠️ You've exceeded your {cat} budget by ${abs(remaining):,.2f}.")
            elif pct >= 0.85:
                col3.markdown(f"🟡 **${remaining:,.2f} left**")
                st.progress(pct)
                st.caption(f"⚠️ You've used {pct*100:.0f}% of your {cat} budget.")
            else:
                col3.markdown(f"🟢 ${remaining:,.2f} left")
                st.progress(pct)
 
            st.markdown("")
        except Exception as e:
            st.warning(f"Could not display row for {row.get('category', 'unknown')}: {e}")