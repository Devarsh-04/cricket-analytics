select d.*
from {{ ref('stg_all_deliveries') }} d
where d.match_id in (select match_id from {{ ref('stg_matches') }})
