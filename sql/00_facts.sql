-- One row per order, with basket metrics and each user's running timeline.
-- The 75k "test" orders have no basket rows, so basket columns are null for them.
create or replace table order_facts as
with basket as (
    select
        op.order_id,
        count(*)                        as basket_size,
        avg(op.reordered)               as reorder_share,
        count(distinct p.department_id) as n_departments
    from order_products op
    join products p using (product_id)
    group by 1
)
select
    o.order_id,
    o.user_id,
    o.eval_set,
    o.order_number,
    o.order_dow,
    o.order_hour_of_day                          as order_hour,
    o.days_since_prior_order                     as gap_days,
    coalesce(o.days_since_prior_order >= 30, false) as is_lapse_return,
    coalesce(sum(o.days_since_prior_order) over (
        partition by o.user_id order by o.order_number
        rows between unbounded preceding and current row
    ), 0)                                        as user_day,
    b.basket_size,
    b.reorder_share,
    b.n_departments
from orders o
left join basket b using (order_id);

-- One row per user. Segments use the median gap between orders.
create or replace table user_facts as
with per_user as (
    select
        user_id,
        count(*)                                                        as n_orders,
        max(user_day)                                                   as span_days,
        median(gap_days)                                                as median_gap,
        avg(gap_days)                                                   as avg_gap,
        avg(is_lapse_return::int) filter (where order_number > 1)       as lapse_share,
        sum(is_lapse_return::int)                                       as n_lapses,
        avg(basket_size)                                                as avg_basket,
        arg_max(gap_days, order_number)                                 as last_gap
    from order_facts
    group by 1
)
select
    *,
    case
        when median_gap <= 7  then '1. Weekly regulars'
        when median_gap <= 14 then '2. Fortnightly'
        when median_gap < 30  then '3. Monthly'
        else                       '4. Drifting (30+ day median gap)'
    end as segment
from per_user;
