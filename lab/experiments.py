"""Experiment design and analysis: sample sizes, A/B readouts, and a geo-lift study.

The A/B test runs on real Instacart users and their real control outcomes; only the
treatment effect is simulated, because no campaign was ever run on this data.
The geo-lift study uses fully synthetic city data, because Instacart has no geography.
"""

import json
from dataclasses import asdict, dataclass

import duckdb
import numpy as np
from scipy import optimize, stats

from lab.config import DB_PATH, OUTPUTS


def sample_size_per_arm(baseline: float, mde_abs: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Users needed in each arm to detect an absolute change of mde_abs in a rate."""
    p1, p2 = baseline, baseline + mde_abs
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    p_bar = (p1 + p2) / 2
    n = (z_a * np.sqrt(2 * p_bar * (1 - p_bar)) + z_b * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / mde_abs**2
    return int(np.ceil(n))


@dataclass
class ABResult:
    n_control: int
    n_treatment: int
    rate_control: float
    rate_treatment: float
    abs_lift: float
    rel_lift: float
    ci_low: float
    ci_high: float
    p_value: float
    srm_p_value: float


def analyze_ab(success_c: int, n_c: int, success_t: int, n_t: int, alpha: float = 0.05) -> ABResult:
    """Two-proportion z-test, with a sample-ratio-mismatch check for a 50/50 split."""
    p_c, p_t = success_c / n_c, success_t / n_t
    pooled = (success_c + success_t) / (n_c + n_t)
    se_pooled = np.sqrt(pooled * (1 - pooled) * (1 / n_c + 1 / n_t))
    p_value = 2 * (1 - stats.norm.cdf(abs(p_t - p_c) / se_pooled))
    se = np.sqrt(p_c * (1 - p_c) / n_c + p_t * (1 - p_t) / n_t)
    z = stats.norm.ppf(1 - alpha / 2)
    srm_p = stats.chisquare([n_c, n_t]).pvalue
    return ABResult(
        n_control=n_c,
        n_treatment=n_t,
        rate_control=p_c,
        rate_treatment=p_t,
        abs_lift=p_t - p_c,
        rel_lift=(p_t - p_c) / p_c,
        ci_low=p_t - p_c - z * se,
        ci_high=p_t - p_c + z * se,
        p_value=float(p_value),
        srm_p_value=float(srm_p),
    )


def rehabit_test(true_lift: float = 0.03, seed: int = 7) -> dict:
    """Post-lapse "re-habit" nudge test on weekly and fortnightly users.

    Unit: an order that came after a 30+ day lapse. Success: the next order arrives
    within 30 days (no second lapse). Control outcomes are what really happened;
    the treatment arm gets a simulated true_lift on top of what really happened.
    """
    con = duckdb.connect(str(DB_PATH), read_only=True)
    outcomes = con.sql("""
        with seq as (
            select f.user_id, f.order_number, f.is_lapse_return, u.segment,
                   lead(f.gap_days) over (partition by f.user_id order by f.order_number) as next_gap
            from order_facts f join user_facts u using (user_id)
        )
        select user_id, (next_gap < 30)::int as success
        from seq
        where is_lapse_return
          and next_gap is not null
          and segment in ('1. Weekly regulars', '2. Fortnightly')
        qualify row_number() over (partition by user_id order by order_number) = 1
        order by user_id
    """).fetchnumpy()["success"]
    con.close()

    rng = np.random.default_rng(seed)
    treated = rng.random(len(outcomes)) < 0.5
    control = outcomes[~treated]
    treatment = outcomes[treated].copy()
    failures = np.flatnonzero(treatment == 0)
    flip_prob = min(1.0, true_lift / max(1e-9, 1 - control.mean()))
    treatment[failures[rng.random(len(failures)) < flip_prob]] = 1

    result = analyze_ab(int(control.sum()), len(control), int(treatment.sum()), len(treatment))
    return {
        "design": {
            "unit": "first post-lapse order per weekly or fortnightly user",
            "success": "next order within 30 days",
            "eligible_users": int(len(outcomes)),
            "baseline_rate": float(outcomes.mean()),
            "simulated_true_lift": true_lift,
            "users_per_arm_for_1pp": sample_size_per_arm(float(outcomes.mean()), 0.01),
            "users_per_arm_for_2pp": sample_size_per_arm(float(outcomes.mean()), 0.02),
        },
        "result": asdict(result),
    }


def synthetic_geo_panel(n_cities: int = 24, n_weeks: int = 16, treat_week: int = 10,
                        n_treated: int = 4, true_lift: float = 0.06, seed: int = 11):
    """Weekly orders for synthetic cities. The first n_treated cities get the campaign."""
    rng = np.random.default_rng(seed)
    base = rng.lognormal(mean=9.5, sigma=0.6, size=n_cities)
    trend = 1 + 0.01 * np.arange(n_weeks)
    season = 1 + 0.05 * np.sin(np.arange(n_weeks) / 2.0)
    city_drift = 1 + rng.normal(0, 0.0015, size=(n_cities, 1)) * np.arange(n_weeks)
    noise = rng.normal(1, 0.03, size=(n_cities, n_weeks))
    orders = base[:, None] * trend * season * city_drift * noise
    treated = np.zeros(n_cities, dtype=bool)
    treated[:n_treated] = True
    orders[treated, treat_week:] *= 1 + true_lift
    return orders, treated, treat_week


def _did(log_orders: np.ndarray, treated: np.ndarray, t0: int) -> float:
    pre, post = slice(0, t0), slice(t0, None)
    did_log = (
        (log_orders[treated, post].mean() - log_orders[treated, pre].mean())
        - (log_orders[~treated, post].mean() - log_orders[~treated, pre].mean())
    )
    return float(np.expm1(did_log))


def geo_lift(true_lift: float = 0.06, seed: int = 11, n_placebos: int = 2000) -> dict:
    """Estimate campaign lift with difference-in-differences and a synthetic control.

    Uncertainty comes from placebo tests: pretend random groups of untreated cities
    got the campaign and see how big a "lift" appears by chance.
    """
    orders, treated, t0 = synthetic_geo_panel(true_lift=true_lift, seed=seed)
    log_orders = np.log(orders)
    pre, post = slice(0, t0), slice(t0, None)
    did = _did(log_orders, treated, t0)

    rng = np.random.default_rng(seed + 1)
    controls = np.flatnonzero(~treated)
    placebo = []
    for _ in range(n_placebos):
        fake = np.zeros(len(controls), dtype=bool)
        fake[rng.choice(len(controls), size=int(treated.sum()), replace=False)] = True
        placebo.append(_did(log_orders[controls], fake, t0))
    placebo = np.array(placebo)

    treated_series = orders[treated].sum(axis=0)
    donors = orders[~treated]
    scale = treated_series[pre].mean()
    weights, _ = optimize.nnls((donors[:, pre] / scale).T, treated_series[pre] / scale)
    synthetic = weights @ donors
    pre_fit_error = float(np.mean(np.abs(synthetic[pre] / treated_series[pre] - 1)))
    sc_lift = float(treated_series[post].sum() / synthetic[post].sum() - 1)

    return {
        "data": "synthetic: 24 cities, 16 weeks, campaign in 4 cities from week 11",
        "true_lift": true_lift,
        "did_estimate": did,
        "did_placebo_p_value": float(np.mean(np.abs(placebo) >= abs(did))),
        "did_placebo_95_range": [float(np.quantile(placebo, 0.025)), float(np.quantile(placebo, 0.975))],
        "synthetic_control_estimate": sc_lift,
        "synthetic_control_pre_period_error": pre_fit_error,
        "weekly": {
            "treated": treated_series.round(1).tolist(),
            "synthetic_control": synthetic.round(1).tolist(),
            "campaign_starts_week": t0 + 1,
        },
    }


def report() -> dict:
    OUTPUTS.mkdir(exist_ok=True)
    out = {"rehabit_test": rehabit_test(), "geo_lift": geo_lift()}
    (OUTPUTS / "experiments.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    print(json.dumps(report(), indent=2)[:3000])
