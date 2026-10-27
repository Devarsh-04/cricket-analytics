select
    d.match_id,
    d.innings,
    {{ clean_team('d.batting_team') }} as batting_team,
    d.over,
    d.ball_seq,
    d.batter,
    d.batter_id,
    d.bowler,
    d.bowler_id,
    d.runs_batter,
    d.runs_extras,
    d.runs_total,
    d.wides,
    d.noballs,
    d.wides = 0 and d.noballs = 0 as is_legal,
    d.is_wicket and d.wicket_kind not in ('retired hurt', 'retired not out') as is_wicket,
    d.player_out,
    d.wicket_kind,
    d.target_runs,
    d.target_overs,
    d.penalty_runs
from {{ source('raw', 'raw_deliveries') }} d
join {{ ref('stg_all_matches') }} m using (match_id)
where not d.is_super_over
  and d.innings in (1, 2)
