select match_id
from {{ ref('stg_all_matches') }}
where (outcome = 'won' and winner is null)
   or (outcome != 'won' and winner is not null)
