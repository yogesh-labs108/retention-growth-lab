-- Is the first order after a lapse different from a normal order?
-- Compared within the same users, so heavy and light users are not mixed.
with lapsers as (
    select user_id from user_facts where n_lapses >= 1
)
select
    case when f.is_lapse_return then 'Order after a 30+ day lapse' else 'Normal order' end as order_type,
    count(*)                    as orders,
    avg(f.basket_size)          as avg_basket_size,
    avg(f.reorder_share)        as avg_reorder_share,
    avg(f.n_departments)        as avg_departments
from order_facts f
join lapsers using (user_id)
where f.order_number > 1 and f.basket_size is not null
group by 1
order by 1;
