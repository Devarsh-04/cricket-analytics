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
),

first_batting as (
    select distinct match_id, batting_team
    from {{ source('raw', 'raw_deliveries') }}
    where innings = 1 and not is_super_over
)

select
    m.match_id,
    m.competition,
    m.start_date,
    year(m.start_date) as season_year,
    case when m.competition = 'bbl' then m.season else cast(year(m.start_date) as varchar) end as season,
    {{ clean_venue('m.venue') }} as venue,
    m.city,
    {{ clean_team('m.team1') }} as team1,
    {{ clean_team('m.team2') }} as team2,
    {{ clean_team('m.winner') }} as winner,
    case
        when m.result = 'tie' then 'tie'
        when m.result = 'no result' then 'no result'
        else 'won'
    end as outcome,
    m.method,
    {{ clean_team('m.eliminator') }} as eliminator,
    {{ clean_team('f.batting_team') }} as bat_first,
    m.result is null
        and m.method is null
        and m.winner is not null
        and m.match_id not in (select match_id from miscounted_overs)
        and m.match_id not in (select match_id from reduced_chases) as has_wp
from {{ source('raw', 'raw_matches') }} m
left join first_batting f using (match_id)
where m.gender = 'male'
  and m.overs = 20
  and (
      m.competition != 't20i'
      or (m.team1 in (select team from full_members) and m.team2 in (select team from full_members))
  )
