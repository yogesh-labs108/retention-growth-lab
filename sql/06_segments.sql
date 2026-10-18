-- User segments by ordering rhythm, with the numbers a lifecycle team would act on.
select
    segment,
    count(*)                                    as users,
    count(*) / sum(count(*)) over ()            as share_of_users,
    sum(n_orders) / sum(sum(n_orders)) over ()  as share_of_orders,
    avg(n_orders)                               as avg_orders,
    avg(avg_gap)                                as avg_gap_days,
    30.0 / avg(avg_gap)                         as orders_per_30_days,
    avg(lapse_share)                            as lapse_rate,
    avg(avg_basket)                             as avg_basket_size,
    avg((last_gap >= 30)::int)                  as share_lapsed_before_last_order
from user_facts
group by 1
order by 1;
