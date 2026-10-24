select distinct d.match_id, d.target_overs
from {{ ref('stg_deliveries') }} d
where d.innings = 2 and d.target_overs is not null and d.target_overs != 20
