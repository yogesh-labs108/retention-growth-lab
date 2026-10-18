-- How likely is a 30+ day gap before each order? Shows whether lapse risk is
-- concentrated early in a user's life.
-- all_users mixes in a survivor effect: frequent users are the ones who reach
-- high order numbers. fixed_cohort follows only users with 20+ orders, so the
-- same people are measured at every step.
with base as (
    select f.order_number, f.is_lapse_return, f.gap_days, u.n_orders
    from order_facts f
    join user_facts u using (user_id)
    where f.order_number between 2 and 20
)
select
    order_number,
    count(*)                                                    as orders_all_users,
    avg(is_lapse_return::int)                                   as lapse_rate_all_users,
    count(*) filter (where n_orders >= 20)                      as orders_fixed_cohort,
    avg(is_lapse_return::int) filter (where n_orders >= 20)     as lapse_rate_fixed_cohort,
    avg(gap_days) filter (where n_orders >= 20)                 as avg_gap_fixed_cohort
from base
group by 1
order by 1;
