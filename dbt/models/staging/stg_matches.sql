select
    match_id,
    competition,
    start_date,
    season_year,
    season,
    venue,
    venue as venue_clean,
    city,
    team1,
    team2,
    winner
from {{ ref('stg_all_matches') }}
where has_wp
