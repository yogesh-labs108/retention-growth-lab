-- Share of users who reach their k-th order. Instacart only includes users with
-- 4+ orders, so the funnel starts at order 4, and depth also reflects how long
-- each user was in the sample window.
with steps(k) as (values (4), (5), (6), (8), (10), (15), (20), (30), (50), (75), (100))
select
    k                                                   as order_number,
    count(*) filter (where u.n_orders >= k)             as users_reaching,
    count(*) filter (where u.n_orders >= k) / count(*)  as share_of_users
from steps
cross join user_facts u
group by k
order by k;
