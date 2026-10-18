"""Fast validation for committed outputs and core analytical invariants."""

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"


def main() -> None:
    required = [
        "segments.csv",
        "habit_transitions.csv",
        "lapse_by_order_number.csv",
        "lapse_return_baskets.csv",
        "category_breadth.csv",
        "department_reorders.csv",
        "order_timing.csv",
        "experiments.json",
        "growth_model.xlsx",
    ]
    missing = [name for name in required if not (OUTPUTS / name).exists()]
    assert not missing, f"Missing generated outputs: {missing}"

    segments = pd.read_csv(OUTPUTS / "segments.csv")
    assert len(segments) == 4
    assert abs(segments["share_of_users"].sum() - 1) < 1e-6
    assert abs(segments["share_of_orders"].sum() - 1) < 1e-6

    transitions = pd.read_csv(OUTPUTS / "habit_transitions.csv")
    weekly = transitions[transitions["segment"] == "1. Weekly regulars"]
    normal = weekly.loc[weekly["this_gap"] == "1. 0-7 days", "next_lapse_rate"].iloc[0]
    after_lapse = weekly.loc[
        weekly["this_gap"] == "4. 30+ days (lapse)", "next_lapse_rate"
    ].iloc[0]
    assert after_lapse > normal * 5

    experiments = json.loads((OUTPUTS / "experiments.json").read_text())
    ab = experiments["rehabit_test"]["result"]
    assert ab["n_control"] + ab["n_treatment"] > 50_000
    assert ab["ci_low"] < ab["abs_lift"] < ab["ci_high"]
    assert experiments["geo_lift"]["data"].startswith("synthetic:")

    print("Validation passed: outputs exist and analytical invariants hold.")


if __name__ == "__main__":
    main()
