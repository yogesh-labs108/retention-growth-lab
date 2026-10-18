-- When do orders happen? Useful for timing reminders and win-back messages.
-- Instacart does not document which number is which weekday, so days stay numbered.
select
    order_dow,
    order_hour,
    count(*)                                  as orders,
    count(*) / sum(count(*)) over ()          as share_of_orders
from order_facts
group by 1, 2
order by 1, 2;
