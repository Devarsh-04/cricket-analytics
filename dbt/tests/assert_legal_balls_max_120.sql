select match_id, innings, 'too many legal balls' as problem
from {{ ref('stg_deliveries') }}
group by match_id, innings
having sum(case when is_legal then 1 else 0 end) > 120
union all
select match_id, 2, 'negative balls_remaining'
from {{ ref('chase_states') }}
where balls_remaining < 0
