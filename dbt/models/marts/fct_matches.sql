-- One row per match, latest snapshot. Team ids are NULL for fixtures whose
-- participants are not yet determined (upcoming knockout rounds).

select
    match_id,
    kickoff_at,
    status,
    matchday,
    stage,
    group_code,
    home_team_id,
    home_team_name,
    away_team_id,
    away_team_name,
    full_time_home_goals,
    full_time_away_goals,
    -- football-data.org's score.fullTime includes penalty-shootout goals when
    -- duration = PENALTY_SHOOTOUT (fullTime = regulation/ET + penalties) — not
    -- "full time" by football convention, and not a real goal for any
    -- goal-counting purpose (a shootout kick isn't a goal scored in the
    -- match). Strip penalties back out so every consumer that counts goals
    -- (totals, scoreline distribution, the Poisson fit) sees the actual match
    -- score; `winner` below already carries the correct shootout-aware
    -- outcome independently of any goal column, so match-result logic
    -- (who won/advanced) is unaffected by this correction.
    case when duration = 'PENALTY_SHOOTOUT'
         then full_time_home_goals - coalesce(penalty_home_goals, 0)
         else full_time_home_goals end as regulation_home_goals,
    case when duration = 'PENALTY_SHOOTOUT'
         then full_time_away_goals - coalesce(penalty_away_goals, 0)
         else full_time_away_goals end as regulation_away_goals,
    half_time_home_goals,
    half_time_away_goals,
    extra_time_home_goals,
    extra_time_away_goals,
    penalty_home_goals,
    penalty_away_goals,
    winner,
    duration,
    last_updated_at,
    extraction_date as snapshot_date

from {{ ref('int_matches_latest') }}
