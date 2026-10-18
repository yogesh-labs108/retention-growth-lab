# Retention & Growth Lab

SQL retention analysis, experiment design, unit economics, and a Streamlit dashboard on **3.42 million Instacart grocery orders** (206,209 users).

**Question:** which quiet users are actually at risk, and what is the cheapest useful action?

## Headline findings

- **Weekly regulars are 25% of users and 49% of orders.**
- **One lapse breaks a habit.** After a 30+ day gap, weekly regulars lapse again 13.2% of the time vs 1.3% normally. For monthly users the gap is just their rhythm (30.3% vs 28.4%).
- **Early-life risk is smaller than it looks.** Across all users, lapse rates fall from 23% to 5%, but that is mostly a survivor effect. Following the same users: 6.7% → 3.8%.
- **Returning users browse.** Post-lapse baskets are the same size, but only 48% of items are repeats vs 61% normally.
- **Blanket coupons lose money.** At ₹30 contribution per order, a win-back coupon breaks even at about ₹6, because most redeemers would have returned anyway.

Decision write-up: [`docs/memo.md`](docs/memo.md).

## What's in the repo

| Part | Path | Role |
|---|---|---|
| SQL | `sql/` | Fact tables, lapse curves, habit transitions, segments, baskets, timing |
| Experiments | `lab/experiments.py` | Sample sizing, A/B readout, geo-lift (DiD / synthetic control / placebo) |
| Unit economics | `outputs/growth_model.xlsx` | Segment LTV, payback, win-back ROI (blue cells = assumptions) |
| AI layer | `lab/ai.py` | Optional plain-English SQL (read-only) and memo draft from computed numbers |
| Dashboard | `app.py` | Streamlit UI over the above |
| Tests | `tests/validate_project.py` | Checks committed outputs stay consistent |

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m lab.pipeline        # downloads ~700MB, builds everything (~4 min)
.venv/bin/python tests/validate_project.py
.venv/bin/streamlit run app.py
```

For AI features, set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (optional `LAB_LLM_MODEL`). Without a key, the memo uses a template and "Ask the data" is off.

## What's real vs not

- **Real:** orders, gaps, baskets, segments, transition rates, A/B control outcomes.
- **Simulated:** A/B treatment lift (no campaign ran on this data).
- **Synthetic:** geo-lift cities (Instacart has no locations).
- **Assumed:** rupee figures and monthly churn (no prices; users stop at last order).
- **Data limits:** gaps capped at 30 days; every user has 4+ orders; no calendar dates.

Data: [Instacart Market Basket Analysis](https://www.kaggle.com/c/instacart-market-basket-analysis), via a [Hugging Face mirror](https://huggingface.co/datasets/attik/Instacart-Market-Basket-Analysis).

## Architecture

```text
Raw CSV
  → DuckDB raw tables
  → order_facts + user_facts
  → SQL metric tables + CSV / Excel outputs
  → Streamlit dashboard
```
