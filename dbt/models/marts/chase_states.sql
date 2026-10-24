with first_innings as (
    select match_id, sum(runs_total) + max(penalty_runs) as first_total
    from {{ ref('stg_deliveries') }}
    where innings = 1
    group by match_id
),

chase as (
    select
        d.*,
        m.competition,
        m.start_date,
        m.season_year,
        m.venue_clean,
        m.winner,
        coalesce(d.target_runs, f.first_total + 1) as target,
        sum(d.runs_total) over w as runs_so_far,
        sum(case when d.is_legal then 1 else 0 end) over w as legal_balls,
        sum(case when d.is_wicket then 1 else 0 end) over w as wickets
    from {{ ref('stg_deliveries') }} d
    join {{ ref('stg_matches') }} m using (match_id)
    left join first_innings f using (match_id)
    where d.innings = 2
    window w as (
        partition by d.match_id
        order by d.over, d.ball_seq
        rows between unbounded preceding and current row
    )
)

select
    match_id,
    competition,
    start_date,
    season_year,
    venue_clean,
    batting_team,
    over,
    ball_seq,
    batter_id,
    batter,
    bowler_id,
    bowler,
    runs_total,
    runs_batter,
    is_wicket,
    is_legal,
    target,
    target - runs_so_far as runs_needed,
    120 - legal_balls as balls_remaining,
    10 - wickets as wickets_in_hand,
    (target - runs_so_far) * 6.0 / nullif(120 - legal_balls, 0) as required_run_rate,
    (winner = batting_team)::int as chase_won
from chase
