import streamlit as st
from datetime import datetime, timedelta
import database as db

st.set_page_config(page_title="Budget Manager", page_icon="📊", layout="wide")

st.title("📊 Budget Manager")
st.caption("Set weekly spending limits per category and track your progress.")

# ── Week selector ─────────────────────────────────────────────────────────────
today = datetime.today()

# Generate last 8 weeks + next week as options
weeks = []
for i in range(-1, 8):
    d = today - timedelta(weeks=i)
    weeks.append(d.strftime("%Y-W%V"))

weeks = sorted(set(weeks), reverse=True)
week_id = st.selectbox("Select week", weeks)

st.divider()

# ── Set / edit budget limits ──────────────────────────────────────────────────
st.subheader("Set limits for this week")
st.caption("Enter $0 to leave a category unbudgeted.")

existing = db.get_budget_vs_actual(week_id)
limit_map = dict(zip(existing["category"], existing["weekly_limit"])) if not existing.empty else {}

with st.form("budget_form"):
    cols = st.columns(2)
    new_limits = {}
    for i, cat in enumerate(db.CATEGORIES):
        current = limit_map.get(cat, 0.0)
        val = cols[i % 2].number_input(
            cat,
            min_value=0.0,
            value=float(current),
            step=5.0,
            format="%.2f",
            key=f"budget_{cat}"
        )
        new_limits[cat] = val

    save = st.form_submit_button("Save budgets")

if save:
    saved_count = 0
    for cat, limit in new_limits.items():
        if limit > 0:
            ok = db.upsert_budget(cat, limit, week_id)
            if ok:
                saved_count += 1
    st.success(f"✅ {saved_count} budget limits saved for {week_id}.")
    st.experimental_rerun()  # Use Streamlit-safe rerun

st.divider()

# ── Budget vs actual ─────────────────────────────────────────────────────────
st.subheader("This week's progress")

df = db.get_budget_vs_actual(week_id)

if df.empty:
    st.info("No budgets set for this week yet. Add limits above to get started.")
else:
    for _, row in df.iterrows():
        cat = row["category"]
        limit = row["weekly_limit"]
        spent = row["total_spent"]
        remaining = row["remaining"]
        over = row["over_budget"]

        # Avoid division by zero
        pct = min(spent / limit, 1.0) if limit > 0 else 0.0

        col1, col2, col3 = st.columns([3, 1, 1])
        col1.markdown(f"**{cat}**")
        col2.markdown(f"${spent:,.2f} / ${limit:,.2f}")

        if over:
            col3.markdown(f"🔴 **Over by ${abs(remaining):,.2f}**")
        elif pct >= 0.85:
            col3.markdown(f"🟡 **${remaining:,.2f} left**")
        else:
            col3.markdown(f"🟢 ${remaining:,.2f} left")

        # Progress bar
        st.progress(pct if not over else 1.0)

        # Optional caption messages
        if over:
            st.caption(f"⚠️ You've exceeded your {cat} budget by ${abs(remaining):,.2f}.")
        elif pct >= 0.85:
            st.caption(f"⚠️ You've used {pct*100:.0f}% of your {cat} budget.")

        st.markdown("")  # spacing between rows
