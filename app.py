"""Retention & Growth Lab dashboard. Run: streamlit run app.py"""

import json

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

from lab import ai
from lab.config import DB_PATH, OUTPUTS
from lab.experiments import analyze_ab, rehabit_test, sample_size_per_arm
from lab.facts import facts

st.set_page_config(page_title="Retention & Growth Lab", layout="wide")


@st.cache_data
def table(name: str) -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.sql(f"select * from m_{name}").df()
    finally:
        con.close()


@st.cache_data
def headline() -> dict:
    return facts()


@st.cache_data
def experiments() -> dict:
    return json.loads((OUTPUTS / "experiments.json").read_text())


@st.cache_data
def rerun_rehabit(lift: float) -> dict:
    return rehabit_test(true_lift=lift)


def stat(col, label: str, value: str, note: str = "") -> None:
    col.metric(label, value)
    if note:
        col.caption(note)


f = headline()
st.title("Retention & Growth Lab")
st.caption(
    f"{f['orders']:,} real grocery orders from {f['users']:,} Instacart users. "
    "Order gaps are capped at 30 days, so a 30 means a lapse of 30+ days. "
    "Every user has 4+ orders, so this is about repeat behaviour, not first-order drop-off."
)

c1, c2, c3, c4 = st.columns(4)
stat(c1, "Weekly regulars: share of users", f"{f['weekly_share_users']:.0%}",
     f"but {f['weekly_share_orders']:.0%} of all orders")
stat(c2, "Weekly regulars: lapse again after a lapse", f"{f['weekly_relapse']:.1%}",
     f"vs {f['weekly_normal_lapse']:.1%} after a normal week")
stat(c3, "Same users, lapse rate at order 2 → 10",
     f"{f['cohort_lapse_order_2']:.1%} → {f['cohort_lapse_order_10']:.1%}", "users with 20+ orders")
stat(c4, "Coupon break-even per redeemed order", f"₹{f['breakeven_incentive']:.0f}",
     "assuming ₹30 contribution per order")

tabs = st.tabs(["Segments", "Lapses", "Baskets", "Timing", "Experiments", "Ask the data"])

with tabs[0]:
    seg = table("segments")
    st.subheader("Who carries the orders")
    long = seg.melt(id_vars="segment", value_vars=["share_of_users", "share_of_orders"],
                    var_name="measure", value_name="share")
    long["measure"] = long["measure"].map({"share_of_users": "Share of users", "share_of_orders": "Share of orders"})
    st.altair_chart(
        alt.Chart(long).mark_bar().encode(
            x=alt.X("share:Q", axis=alt.Axis(format="%"), title=None),
            y=alt.Y("segment:N", title=None),
            color=alt.Color("measure:N", title=None),
            yOffset="measure:N",
            tooltip=["segment", "measure", alt.Tooltip("share:Q", format=".1%")],
        ).properties(height=260),
        use_container_width=True,
    )
    st.dataframe(seg.style.format({
        "share_of_users": "{:.1%}", "share_of_orders": "{:.1%}", "avg_orders": "{:.1f}",
        "avg_gap_days": "{:.1f}", "orders_per_30_days": "{:.2f}", "lapse_rate": "{:.1%}",
        "avg_basket_size": "{:.1f}", "share_lapsed_before_last_order": "{:.1%}",
    }), hide_index=True, width="stretch")

with tabs[1]:
    st.subheader("Lapse risk by order number")
    st.caption("All users mixes in a survivor effect. The fixed cohort follows the same "
               "53,931 users (20+ orders) at every step.")
    lap = table("lapse_by_order_number")
    lap_long = lap.melt(id_vars="order_number", value_vars=["lapse_rate_all_users", "lapse_rate_fixed_cohort"],
                        var_name="series", value_name="lapse_rate")
    lap_long["series"] = lap_long["series"].map({
        "lapse_rate_all_users": "All users", "lapse_rate_fixed_cohort": "Fixed cohort (20+ orders)"})
    st.altair_chart(
        alt.Chart(lap_long).mark_line(point=True).encode(
            x=alt.X("order_number:Q", title="Order number", axis=alt.Axis(tickMinStep=1, format="d")),
            y=alt.Y("lapse_rate:Q", axis=alt.Axis(format="%"), title="Orders after a 30+ day gap"),
            color=alt.Color("series:N", title=None),
            tooltip=["order_number", "series", alt.Tooltip("lapse_rate:Q", format=".1%")],
        ).properties(height=300),
        use_container_width=True,
    )

    st.subheader("Does one lapse lead to another?")
    st.caption("Chance that the next gap is also 30+ days, given the gap before this order.")
    tr = table("habit_transitions").dropna(subset=["segment"])
    st.altair_chart(
        alt.Chart(tr).mark_rect().encode(
            x=alt.X("this_gap:N", title="Gap before this order", axis=alt.Axis(labelAngle=0, orient="top")),
            y=alt.Y("segment:N", title=None, axis=alt.Axis(labelLimit=260)),
            color=alt.Color("next_lapse_rate:Q", title="Next gap 30+", legend=None,
                            scale=alt.Scale(scheme="orangered")),
            tooltip=["segment", "this_gap", alt.Tooltip("next_lapse_rate:Q", format=".1%"), "transitions"],
        ).properties(height=280)
        + alt.Chart(tr).mark_text(fontSize=14, color="black").encode(
            x="this_gap:N", y="segment:N", text=alt.Text("next_lapse_rate:Q", format=".1%")),
        use_container_width=True,
    )

with tabs[2]:
    left, right = st.columns(2)
    with left:
        st.subheader("The order after a lapse")
        st.caption("Same users, comparing their post-lapse orders with their normal orders.")
        st.dataframe(table("lapse_return_baskets").style.format({
            "avg_basket_size": "{:.2f}", "avg_reorder_share": "{:.1%}", "avg_departments": "{:.2f}"}),
            hide_index=True, width="stretch")
        st.caption("Basket size barely moves, but fewer items are repeats: returning users "
                   "re-browse instead of re-ordering their usuals.")
    with right:
        st.subheader("Early breadth vs later lapse")
        st.caption("Departments shopped in orders 1-3, within basket-size groups. Correlation only.")
        cb = table("category_breadth")
        st.altair_chart(
            alt.Chart(cb).mark_line(point=True).encode(
                x=alt.X("early_breadth:N", sort=None, title="Departments in first 3 orders"),
                y=alt.Y("later_lapse_rate:Q", axis=alt.Axis(format="%"), title="Lapse rate from order 4"),
                color=alt.Color("basket_size_group:N", title=None),
                tooltip=["basket_size_group", "early_breadth", "users",
                         alt.Tooltip("later_lapse_rate:Q", format=".1%")],
            ).properties(height=280),
            use_container_width=True,
        )
    st.subheader("Which departments build habit")
    dep = table("department_reorders")
    st.altair_chart(
        alt.Chart(dep).mark_bar().encode(
            x=alt.X("reorder_rate:Q", axis=alt.Axis(format="%"), title="Reorder rate"),
            y=alt.Y("department:N", sort="-x", title=None),
            tooltip=["department", alt.Tooltip("reorder_rate:Q", format=".1%"),
                     alt.Tooltip("share_of_items:Q", format=".1%")],
        ).properties(height=440),
        use_container_width=True,
    )

with tabs[3]:
    st.subheader("When orders happen")
    st.caption("Instacart does not say which day number is which weekday.")
    tm = table("order_timing")
    st.altair_chart(
        alt.Chart(tm).mark_rect().encode(
            x=alt.X("order_hour:O", title="Hour of day"),
            y=alt.Y("order_dow:O", title="Day (0-6)"),
            color=alt.Color("share_of_orders:Q", title="Share", scale=alt.Scale(scheme="blues")),
            tooltip=["order_dow", "order_hour", "orders", alt.Tooltip("share_of_orders:Q", format=".2%")],
        ).properties(height=260),
        use_container_width=True,
    )

with tabs[4]:
    exp = experiments()
    st.subheader("1. Size the test before running it")
    a, b, c = st.columns(3)
    baseline = a.number_input("Baseline rate", 0.01, 0.99, round(f["rehabit_baseline"], 3), 0.01)
    mde = b.number_input("Smallest lift worth detecting (absolute)", 0.001, 0.2, 0.01, 0.005, format="%.3f")
    power = c.selectbox("Power", [0.8, 0.9], index=0)
    n = sample_size_per_arm(baseline, mde, power=power)
    st.write(f"**{n:,} users per arm** ({2 * n:,} total). "
             f"{f['rehabit_eligible_users']:,} users are eligible for the re-habit test.")

    st.subheader("2. Re-habit nudge test: real users, simulated effect")
    d = exp["rehabit_test"]["design"]
    st.caption(f"Unit: {d['unit']}. Success: {d['success']}. Control outcomes are what really "
               "happened; the treatment effect is simulated because no campaign ran on this data.")
    lift = st.slider("Simulated true lift (absolute points)", 0.0, 0.06, 0.03, 0.005, format="%.3f")
    st.caption("Set the lift to 0 to see a false alarm: across 1,000 random splits with no real "
               "effect, 5.6% came out significant at p < 0.05, which is what that threshold allows.")
    r = rerun_rehabit(lift)["result"]
    k1, k2, k3, k4 = st.columns(4)
    stat(k1, "Control", f"{r['rate_control']:.2%}", f"n = {r['n_control']:,}")
    stat(k2, "Treatment", f"{r['rate_treatment']:.2%}", f"n = {r['n_treatment']:,}")
    stat(k3, "Measured lift", f"{r['abs_lift'] * 100:+.2f} pts",
         f"95% CI {r['ci_low'] * 100:+.2f} to {r['ci_high'] * 100:+.2f}")
    stat(k4, "p-value", "< 0.001" if r["p_value"] < 0.001 else f"{r['p_value']:.3f}",
         f"50/50 split check p = {r['srm_p_value']:.2f}")

    st.subheader("3. Read your own test")
    a, b, c, d2 = st.columns(4)
    sc = a.number_input("Control successes", 0, value=830)
    nc = b.number_input("Control users", 1, value=1000)
    stt = c.number_input("Treatment successes", 0, value=860)
    nt = d2.number_input("Treatment users", 1, value=1000)
    if sc <= nc and stt <= nt:
        own = analyze_ab(int(sc), int(nc), int(stt), int(nt))
        st.write(f"Lift **{own.abs_lift * 100:+.2f} pts** (95% CI {own.ci_low * 100:+.2f} to "
                 f"{own.ci_high * 100:+.2f}), p = {own.p_value:.3f}, split check p = {own.srm_p_value:.2f}.")

    st.subheader("4. Geo-lift study (synthetic cities)")
    g = exp["geo_lift"]
    st.caption(f"{g['data']}. True lift {g['true_lift']:.0%}. Difference-in-differences: "
               f"{g['did_estimate']:.1%} (placebo range {g['did_placebo_95_range'][0]:+.1%} to "
               f"{g['did_placebo_95_range'][1]:+.1%}). Synthetic control: {g['synthetic_control_estimate']:.1%}.")
    weeks = list(range(1, len(g["weekly"]["treated"]) + 1))
    geo = pd.DataFrame({"week": weeks * 2,
                        "series": ["Test cities"] * len(weeks) + ["Synthetic control"] * len(weeks),
                        "orders": g["weekly"]["treated"] + g["weekly"]["synthetic_control"]})
    start = g["weekly"]["campaign_starts_week"]
    st.altair_chart(
        alt.Chart(geo).mark_line(point=True).encode(
            x=alt.X("week:Q", title="Week"), y=alt.Y("orders:Q", title="Weekly orders", scale=alt.Scale(zero=False)),
            color=alt.Color("series:N", title=None))
        + alt.Chart(pd.DataFrame({"week": [start - 0.5]})).mark_rule(strokeDash=[4, 4]).encode(x="week:Q"),
        use_container_width=True,
    )

with tabs[5]:
    st.subheader("Weekly growth memo")
    if st.button("Draft memo"):
        text, source = ai.memo(f)
        st.caption(f"Written by: {source}")
        st.markdown(text)
    if not ai.available():
        st.caption("No LLM key set, so the memo uses a template. Set OPENAI_API_KEY or "
                   "ANTHROPIC_API_KEY to draft it with a model and to enable questions below.")

    st.subheader("Ask the data")
    q = st.text_input("Question", "Which department has the lowest reorder rate among weekly regulars?",
                      disabled=not ai.available())
    if ai.available() and st.button("Ask"):
        try:
            sql, df = ai.ask(q)
            st.code(sql, language="sql")
            st.dataframe(df, width="stretch")
        except Exception as e:
            st.error(str(e))
