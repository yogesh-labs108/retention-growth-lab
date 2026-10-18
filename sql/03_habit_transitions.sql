-- Given the gap before this order, what does the gap before the next order look like?
-- Answers: once a user lapses, do they snap back to their habit or keep drifting?
-- Split by segment so a "lapse spiral" is not just monthly users looking monthly.
with gaps as (
    select
        f.user_id,
        u.segment,
        f.gap_days,
        lead(f.gap_days) over (partition by f.user_id order by f.order_number) as next_gap
    from order_facts f
    join user_facts u using (user_id)
    where f.order_number > 1
),
bucketed as (
    select
        segment,
        case
            when gap_days <= 7  then '1. 0-7 days'
            when gap_days <= 14 then '2. 8-14 days'
            when gap_days < 30  then '3. 15-29 days'
            else                     '4. 30+ days (lapse)'
        end as this_gap,
        next_gap >= 30 as next_is_lapse
    from gaps
    where next_gap is not null
)
select
    segment,
    this_gap,
    count(*)                    as transitions,
    avg(next_is_lapse::int)     as next_lapse_rate
from bucketed
group by grouping sets ((this_gap), (segment, this_gap))
order by segment nulls first, this_gap;
