"""AI layer: ask the data in plain English, and draft a growth memo from the metrics.

Needs OPENAI_API_KEY or ANTHROPIC_API_KEY. Set LAB_LLM_MODEL to pick a model.
Without a key, the memo falls back to a plain template and "ask" is disabled.
Generated SQL only runs on a read-only connection, one SELECT at a time.
"""

import json
import os
import re
import urllib.request

import duckdb

from lab.config import DB_PATH

SCHEMA = """
Tables (DuckDB):
- order_facts(order_id, user_id, eval_set, order_number, order_dow, order_hour, gap_days,
  is_lapse_return, user_day, basket_size, reorder_share, n_departments)
  gap_days = days since the user's previous order, capped at 30 (30 means 30 or more).
  is_lapse_return = this order came after a 30+ day gap.
- user_facts(user_id, n_orders, span_days, median_gap, avg_gap, lapse_share, n_lapses,
  avg_basket, last_gap, segment)
  segment is one of '1. Weekly regulars', '2. Fortnightly', '3. Monthly',
  '4. Drifting (30+ day median gap)'.
- order_products(order_id, product_id, add_to_cart_order, reordered)
- products(product_id, product_name, aisle_id, department_id)
- aisles(aisle_id, aisle), departments(department_id, department)
There are no prices, dates, or locations. Every user has at least 4 orders.
"""


def _provider():
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def available() -> bool:
    return _provider() is not None


def _complete(system: str, user: str) -> str:
    provider = _provider()
    if provider == "openai":
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps({
                "model": os.environ.get("LAB_LLM_MODEL", "gpt-4o-mini"),
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0,
            }).encode(),
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)["choices"][0]["message"]["content"]
    if provider == "anthropic":
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({
                "model": os.environ.get("LAB_LLM_MODEL", "claude-3-5-haiku-latest"),
                "max_tokens": 1200,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            }).encode(),
            headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)["content"][0]["text"]
    raise RuntimeError("No LLM key set. Export OPENAI_API_KEY or ANTHROPIC_API_KEY.")


def _clean_sql(text: str) -> str:
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S)
    sql = (match.group(1) if match else text).strip().rstrip(";").strip()
    if ";" in sql:
        raise ValueError("Only one statement is allowed.")
    if not re.match(r"^(select|with)\b", sql, re.I):
        raise ValueError("Only SELECT queries are allowed.")
    return sql


def ask(question: str, limit: int = 200):
    """Turn a question into SQL, run it read-only, and return (sql, dataframe)."""
    sql = _clean_sql(_complete(
        "You write one DuckDB SELECT query that answers the question. "
        "Return only the SQL in a ```sql block. Prefer aggregates over raw rows.\n" + SCHEMA,
        question,
    ))
    con = duckdb.connect(str(DB_PATH), read_only=True, config={"enable_external_access": False})
    try:
        df = con.sql(f"select * from ({sql}) limit {int(limit)}").df()
    finally:
        con.close()
    return sql, df


def memo(facts: dict) -> tuple:
    """A short growth memo and its source: the LLM when a key works, otherwise a template."""
    if available():
        try:
            return _complete(
                "You are a growth analyst writing a short internal memo for a food and grocery "
                "delivery team. Use only the numbers given. Do not invent figures. Structure: "
                "What we found (3 bullets), What I would test next (3 experiments with metric "
                "and success threshold), Caveats (2 bullets). Under 300 words.",
                json.dumps(facts, indent=2),
            ), "model"
        except Exception as e:
            return template_memo(facts), f"template (model call failed: {e})"
    return template_memo(facts), "template"


def template_memo(f: dict) -> str:
    return f"""**What we found**
- Weekly regulars are {f['weekly_share_users']:.0%} of users but {f['weekly_share_orders']:.0%} of orders.
- After one lapse, weekly regulars lapse again {f['weekly_relapse']:.1%} of the time, against {f['weekly_normal_lapse']:.1%} normally.
- For monthly users a 30-day gap is their rhythm: {f['monthly_relapse']:.1%} after a lapse vs {f['monthly_normal_lapse']:.1%} otherwise.

**What I would test next**
- A free re-habit nudge after a lapse for weekly and fortnightly users. Metric: next order within 30 days. Ship if lift is at least 1 point ({f['n_per_arm_1pp']:,} users per arm).
- The same nudge with a coupon, to price the incentive. Break-even is about ₹{f['breakeven_incentive']:.0f} per redeemed order.
- Hold back a city group to measure total lift with a geo test.

**Caveats**
- Instacart has no prices, dates, or locations, so money figures are assumptions.
- Users only appear up to their last order, so true churn is not measurable here.
"""
