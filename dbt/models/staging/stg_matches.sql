with full_members as (
    select unnest([
        'Afghanistan', 'Australia', 'Bangladesh', 'England', 'India', 'Ireland',
        'New Zealand', 'Pakistan', 'South Africa', 'Sri Lanka', 'West Indies', 'Zimbabwe'
    ]) as team
),

-- umpire miscounts (7-ball overs) push some innings past 120 legal balls
miscounted_overs as (
    select distinct match_id
    from {{ source('raw', 'raw_deliveries') }}
    where not is_super_over
    group by match_id, innings
    having sum(case when wides = 0 and noballs = 0 then 1 else 0 end) > 120
),

-- chases shortened before they started (no DLS method recorded) break the 120-ball clock
reduced_chases as (
    select distinct match_id
    from {{ source('raw', 'raw_deliveries') }}
    where innings = 2 and target_overs is not null and target_overs != 20
)

select
    match_id,
    competition,
    start_date,
    year(start_date) as season_year,
    venue,
    trim(split_part(venue, ',', 1)) as venue_clean,
    city,
    team1,
    team2,
    winner
from {{ source('raw', 'raw_matches') }}
where gender = 'male'
  and overs = 20
  and result is null
  and method is null
  and winner is not null
  and match_id not in (select match_id from miscounted_overs)
  and match_id not in (select match_id from reduced_chases)
  and (
      competition != 't20i'
      or (team1 in (select team from full_members) and team2 in (select team from full_members))
  )
