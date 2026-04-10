import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime
import database as db

db.init_db()

st.set_page_config(page_title="Spending Tracker", page_icon="💳", layout="wide")
st.title("💳 Spending Tracker")
st.caption("Your personal finance dashboard")

# ── Month selector ────────────────────────────────────────────────────────────
today        = datetime.today()
all_months   = [(today.year, m) for m in range(1, today.month + 1)]
month_labels = {(y, m): datetime(y, m, 1).strftime("%B %Y") for y, m in all_months}

selected    = st.selectbox(
    "Select month",
    options=list(reversed(all_months)),
    format_func=lambda x: month_labels[x]
)
year, month = selected

# ── Fetch data ────────────────────────────────────────────────────────────────
df_month  = db.get_transactions_by_month(year, month)
df_cat    = db.get_category_summary(year, month)
df_weekly = db.get_weekly_summary(year, month)
df_monthly = db.get_monthly_summary()

st.divider()

# ── KPI metrics ───────────────────────────────────────────────────────────────
if not df_month.empty and "amount" in df_month.columns:
    total   = float(df_month["amount"].sum())
    count   = len(df_month)
    avg     = float(df_month["amount"].mean()) if count > 0 else 0.0
    largest = float(df_month["amount"].max())  if count > 0 else 0.0
else:
    total, count, avg, largest = 0.0, 0, 0.0, 0.0

# delta vs prior month
prior_months = [(y, m) for y, m in all_months if (y, m) < selected]
delta_str    = None
if prior_months:
    py, pm   = prior_months[-1]
    prior_df = db.get_transactions_by_month(py, pm)
    if not prior_df.empty and "amount" in prior_df.columns:
        prior_tot = float(prior_df["amount"].sum())
        if prior_tot > 0:
            pct       = ((total - prior_tot) / prior_tot) * 100
            delta_str = f"{pct:+.1f}% vs {month_labels[(py, pm)]}"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total spent",      f"${total:,.2f}",  delta_str)
c2.metric("Transactions",     str(count))
c3.metric("Avg transaction",  f"${avg:,.2f}")
c4.metric("Largest purchase", f"${largest:,.2f}")

st.divider()

# ── Month-to-month bar chart ──────────────────────────────────────────────────
st.subheader("Month-to-month spending")
if df_monthly.empty:
    st.info("No data yet.")
else:
    def fmt_month(m):
        try:
            return datetime.strptime(str(m)[:7], "%Y-%m").strftime("%b %Y")
        except:
            return str(m)
    df_monthly["month_label"] = df_monthly["month"].apply(fmt_month)
    df_monthly["total_spent"] = df_monthly["total_spent"].astype(float)
    fig = px.bar(
        df_monthly, x="month_label", y="total_spent",
        labels={"month_label": "", "total_spent": "Total spent ($)"},
        color_discrete_sequence=["#378ADD"]
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=0, r=0), height=280,
        yaxis=dict(tickprefix="$", gridcolor="rgba(128,128,128,0.15)"),
        xaxis=dict(showgrid=False), bargap=0.35
    )
    fig.update_traces(marker_line_width=0)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Spending trend line chart ─────────────────────────────────────────────────
st.subheader("Spending trend")
if df_monthly.empty:
    st.info("No data yet.")
else:
    fig2 = px.line(
        df_monthly, x="month_label", y="total_spent",
        labels={"month_label": "", "total_spent": "Total spent ($)"},
        markers=True, color_discrete_sequence=["#1D9E75"]
    )
    fig2.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=0, r=0), height=260,
        yaxis=dict(tickprefix="$", gridcolor="rgba(128,128,128,0.15)"),
        xaxis=dict(showgrid=False)
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Weekly breakdown ──────────────────────────────────────────────────────────
st.subheader("Weekly breakdown")
if df_weekly.empty:
    st.info("No transactions this month.")
else:
    df_weekly["total_spent"] = df_weekly["total_spent"].astype(float)
    df_weekly["week_label"]  = df_weekly["week_id"].apply(
        lambda w: f"Week {w.split('W')[-1]}" if isinstance(w, str) and "W" in w else str(w)
    )
    fig3 = px.bar(
        df_weekly, x="week_label", y="total_spent",
        labels={"week_label": "", "total_spent": "Spent ($)"},
        color_discrete_sequence=["#EF9F27"],
        text="total_spent"
    )
    fig3.update_traces(
        texttemplate="$%{text:,.0f}", textposition="outside", marker_line_width=0
    )
    fig3.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=24, b=10, l=0, r=0), height=280,
        yaxis=dict(tickprefix="$", gridcolor="rgba(128,128,128,0.15)"),
        xaxis=dict(showgrid=False), bargap=0.4
    )
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── Category breakdown ────────────────────────────────────────────────────────
st.subheader("Category breakdown")
if df_cat.empty:
    st.info("No transactions this month.")
else:
    df_cat["total_spent"]  = df_cat["total_spent"].astype(float)
    col_chart, col_table   = st.columns([2, 3])

    with col_chart:
        fig4 = px.pie(
            df_cat, names="category", values="total_spent",
            hole=0.5, color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig4.update_traces(textposition="outside", textinfo="label+percent", showlegend=False)
        fig4.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=10, l=10, r=10), height=320
        )
        st.plotly_chart(fig4, use_container_width=True)

    with col_table:
        display      = df_cat.copy()
        display["pct"] = (display["total_spent"] / display["total_spent"].sum() * 100).round(1)
        display = display.rename(columns={
            "category":     "Category",
            "transactions": "Transactions",
            "total_spent":  "Total ($)",
            "pct":          "% of spending"
        })
        display["Total ($)"]     = display["Total ($)"].map("${:,.2f}".format)
        display["% of spending"] = display["% of spending"].map("{:.1f}%".format)
        st.dataframe(
            display[["Category", "Total ($)", "Transactions", "% of spending"]],
            use_container_width=True, hide_index=True
        )