"""The headline numbers, pulled from the metric tables and the experiment report."""

import json

import duckdb

from lab.config import DB_PATH, OUTPUTS

CONTRIBUTION_PER_ORDER = 30
MESSAGE_COST = 0.5
EXTRA_ORDERS_PER_RETAINED_USER = 6


def facts() -> dict:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    seg = {r[0][:2]: r for r in con.sql(
        "select segment, share_of_users, share_of_orders, lapse_rate from m_segments").fetchall()}
    trans = {(r[0], r[1]): r[2] for r in con.sql(
        "select coalesce(segment, 'all'), this_gap, next_lapse_rate from m_habit_transitions").fetchall()}
    cohort = con.sql(
        "select order_number, lapse_rate_fixed_cohort from m_lapse_by_order_number order by 1").fetchall()
    totals = con.sql("select count(*), count(distinct user_id) from order_facts").fetchone()
    con.close()

    exp = json.loads((OUTPUTS / "experiments.json").read_text())
    design = exp["rehabit_test"]["design"]
    lift = design["simulated_true_lift"]
    n = design["eligible_users"]
    contribution = n * lift * EXTRA_ORDERS_PER_RETAINED_USER * CONTRIBUTION_PER_ORDER
    redeemers = n * (design["baseline_rate"] + lift)

    def normal_lapse(segment):
        return trans[(segment, "1. 0-7 days")] if segment.startswith("1.") else trans[(segment, "2. 8-14 days")]

    return {
        "orders": totals[0],
        "users": totals[1],
        "weekly_share_users": seg["1."][1],
        "weekly_share_orders": seg["1."][2],
        "monthly_plus_share_users": seg["3."][1] + seg["4."][1],
        "monthly_plus_share_orders": seg["3."][2] + seg["4."][2],
        "weekly_relapse": trans[("1. Weekly regulars", "4. 30+ days (lapse)")],
        "weekly_normal_lapse": normal_lapse("1. Weekly regulars"),
        "fortnightly_relapse": trans[("2. Fortnightly", "4. 30+ days (lapse)")],
        "fortnightly_normal_lapse": normal_lapse("2. Fortnightly"),
        "monthly_relapse": trans[("3. Monthly", "4. 30+ days (lapse)")],
        "monthly_normal_lapse": trans[("3. Monthly", "3. 15-29 days")],
        "cohort_lapse_order_2": cohort[0][1],
        "cohort_lapse_order_10": dict(cohort)[10],
        "rehabit_eligible_users": n,
        "rehabit_baseline": design["baseline_rate"],
        "n_per_arm_1pp": design["users_per_arm_for_1pp"],
        "n_per_arm_2pp": design["users_per_arm_for_2pp"],
        "breakeven_incentive": (contribution - n * MESSAGE_COST) / redeemers,
        "geo_true_lift": exp["geo_lift"]["true_lift"],
        "geo_did_estimate": exp["geo_lift"]["did_estimate"],
        "geo_sc_estimate": exp["geo_lift"]["synthetic_control_estimate"],
    }


if __name__ == "__main__":
    for k, v in facts().items():
        print(f"{k:>28}: {v:.4f}" if isinstance(v, float) else f"{k:>28}: {v:,}")
