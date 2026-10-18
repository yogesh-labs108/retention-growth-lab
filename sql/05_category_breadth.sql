-- Do users who shop more departments in their first 3 orders lapse less later?
-- Split by basket size so "bigger baskets" is not mistaken for "broader baskets".
-- This is correlation, not proof that cross-category nudges cause retention.
with early as (
    select
        f.user_id,
        count(distinct p.department_id) as early_departments,
        count(*) / 3.0                  as early_items_per_order
    from order_facts f
    join order_products op using (order_id)
    join products p using (product_id)
    where f.order_number <= 3
    group by 1
),
later as (
    select user_id, avg(is_lapse_return::int) as later_lapse_rate
    from order_facts
    where order_number >= 4
    group by 1
),
joined as (
    select
        e.*,
        l.later_lapse_rate,
        ntile(3) over (order by e.early_items_per_order, e.user_id) as basket_tercile
    from early e
    join later l using (user_id)
)
select
    case basket_tercile when 1 then '1. Small baskets' when 2 then '2. Medium baskets' else '3. Large baskets' end
                                                        as basket_size_group,
    case
        when early_departments <= 3  then '1-3 departments'
        when early_departments <= 6  then '4-6 departments'
        when early_departments <= 9  then '7-9 departments'
        else                              '10+ departments'
    end                                                 as early_breadth,
    count(*)                                            as users,
    avg(later_lapse_rate)                               as later_lapse_rate
from joined
group by 1, 2
order by 1, min(early_departments);
