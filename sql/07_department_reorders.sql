-- Which departments drive habit (high reorder share) and which are one-off?
select
    d.department,
    count(*)                                  as items,
    count(*) / sum(count(*)) over ()          as share_of_items,
    avg(op.reordered)                         as reorder_rate,
    count(distinct f.user_id)                 as users
from order_products op
join products p using (product_id)
join departments d using (department_id)
join order_facts f using (order_id)
group by 1
order by items desc;
