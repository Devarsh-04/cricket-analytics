with teams as (
    select team1 as name from {{ ref('stg_all_matches') }}
    union all select team2 from {{ ref('stg_all_matches') }}
    union all select winner from {{ ref('stg_all_matches') }}
    union all select bat_first from {{ ref('stg_all_matches') }}
    union all select eliminator from {{ ref('stg_all_matches') }}
    union all select distinct batting_team from {{ ref('stg_all_deliveries') }}
)
select name from teams where name in (select alias from {{ ref('team_aliases') }})
union all
select venue from {{ ref('stg_all_matches') }} where venue in (select alias from {{ ref('venue_aliases') }})
