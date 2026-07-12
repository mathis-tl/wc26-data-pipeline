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
