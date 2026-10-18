# How I'd bring back lapsed food-delivery users

**Yogesh T · Retention & Growth Lab · October 2026**

Built on 3.42 million real grocery orders from 206,209 Instacart users. Swiggy's data is not public, so this is a stand-in: the same repeat-ordering problem, measured on real behaviour. Money figures are assumptions and are labelled as such.

## The short version

Don't send win-back coupons to everyone who goes quiet. Spend the effort on **frequent users right after their first lapse**. That's where one missed month turns into a lost customer. For monthly users a 30-day gap is just their rhythm. And the first test should be a **free nudge**, because at realistic margins a blanket coupon loses money.

## What the data says

**1. A quarter of users carry half the orders.**
Weekly regulars are 25.5% of users and 48.9% of orders. Monthly and drifting users are 43.9% of users but only 21.7% of orders.

**2. One lapse sharply raises the risk of another, but only for habitual users.**
Chance that the next gap is also 30+ days:

| Segment | After a normal gap | After a 30+ day lapse |
|---|---|---|
| Weekly regulars | 1.3% | **13.2%** (10x) |
| Fortnightly | 8.5% | **18.0%** (2x) |
| Monthly | 28.4% | 30.3% (no real change) |

For a weekly user, one quiet month is the moment the habit breaks. For a monthly user it's a normal month.

**3. Early-life risk is real but smaller than it first looks.**
Across all users, the lapse rate falls from 23% at order 2 to 5% at order 20. Most of that is a survivor effect, because frequent users are the ones who reach order 20. Following the same 53,931 users (20+ orders) from order to order, it falls from 6.7% to 3.8% by order 10. The first ten orders still matter, but the gain is about a 3-point drop, not 18.

**4. Returning users browse; they don't re-order.**
A user's first order after a lapse is the same size as their normal orders (10.0 vs 9.9 items), but only 48% of items are repeats, against 61% normally. A "your usual basket" message is aimed at the wrong behaviour. Returning users are re-discovering the app.

**5. Pushing early cross-category shopping is not a retention lever here.**
Within the same basket size, users who shopped more departments in their first three orders lapsed *slightly more* later, not less (medium baskets: 20.2% at 1–3 departments, 25.4% at 10+). That's correlation, not proof. But it means "get them into more categories" needs its own test before it gets credit for retention.

## What I would test

**Test 1: a free re-habit nudge after the first lapse** (weekly and fortnightly users)
- Trigger: the first order after a 30+ day gap.
- Message: lead with what's new or seasonal, not "reorder your usuals" (finding 4).
- Success metric: next order within 30 days. The baseline is 83.4%.
- Size: 21,219 users per arm to detect a 1-point lift; 59,516 users are eligible.
- Guardrails: opt-outs and order frequency in the following 60 days.
- Simulated readout: with a true 3-point lift, the test measured +3.2 points (95% CI 2.7 to 3.8). With no real lift, about 1 run in 20 still looks significant, which is why the threshold and sample size are fixed before launch.

**Test 2: price the coupon before scaling it**
At ₹30 contribution per order, a coupon breaks even at about **₹6 per redeemed order**. Most redeemers would have come back anyway (83% baseline), so a ₹75 coupon to all 59,516 eligible users costs about ₹38.6 lakh to buy about ₹3.2 lakh of extra contribution. If coupons are used at all, target the users the model says are most likely to lapse again, and test 2–3 coupon values against the free nudge.

**Test 3: measure total impact with a city holdout**
Run the winning treatment in a few cities and compare against matched cities. On synthetic data (24 cities, true lift 6%), difference-in-differences estimated 4.4%, a synthetic control 4.1%, and placebo tests put chance results within about ±1.8%. Four test cities are enough to see a 6% effect but not to measure it precisely. Use more cities or a longer window if the size of the lift matters for the budget.

## Caveats

- Instacart is US grocery, not Indian food delivery. Order rhythms differ, so the patterns need checking against Swiggy's own data before anything ships.
- The data has no prices, dates, or locations. Gaps are capped at 30 days, and every user has 4+ orders, so first-order drop-off and true churn can't be measured.
- The A/B treatment effect is simulated on real control outcomes. The geo-lift study is fully synthetic.
