with first_innings as (
    select match_id, sum(runs_total) + max(penalty_runs) as first_total
    from {{ ref('stg_deliveries') }}
    where innings = 1
    group by match_id
),
targets as (
    select distinct match_id, target_runs
    from {{ ref('stg_deliveries') }}
    where innings = 2 and target_runs is not null and target_overs = 20
)
select t.match_id, t.target_runs, f.first_total
from targets t
join first_innings f using (match_id)
where t.target_runs != f.first_total + 1
