-- Regression guard for the penalty-shootout goal-counting bug (fixed
-- 2026-08-07): regulation_*_goals must equal full_time_*_goals minus
-- penalties on shootout matches, and must equal full_time_*_goals exactly on
-- every other match. A row here means either football-data.org's score
-- schema changed shape, or a future edit reintroduced shootout-inflated
-- goals into a goal-counting column.

select match_id, duration, full_time_home_goals, full_time_away_goals,
       penalty_home_goals, penalty_away_goals,
       regulation_home_goals, regulation_away_goals
from {{ ref('fct_matches') }}
where full_time_home_goals is not null
  and (
    (duration = 'PENALTY_SHOOTOUT'
      and (regulation_home_goals != full_time_home_goals - coalesce(penalty_home_goals, 0)
        or regulation_away_goals != full_time_away_goals - coalesce(penalty_away_goals, 0)))
    or
    (coalesce(duration, '') != 'PENALTY_SHOOTOUT'
      and (regulation_home_goals != full_time_home_goals
        or regulation_away_goals != full_time_away_goals))
  )
