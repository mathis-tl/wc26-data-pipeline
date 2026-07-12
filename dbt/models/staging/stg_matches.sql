-- One row per match per extraction_date: the snapshot history is kept here,
-- latest-snapshot filtering happens in the marts.

with source as (

    select * from {{ source('football_data', 'matches') }}

)

select
    id                                as match_id,
    cast(utcDate as timestamp)        as kickoff_at,
    status,
    matchday,
    stage,
    -- matches encode the group as 'GROUP_A'; canonical form is the letter
    replace("group", 'GROUP_', '')    as group_code,
    homeTeam.id                       as home_team_id,
    homeTeam.name                     as home_team_name,
    homeTeam.tla                      as home_team_tla,
    awayTeam.id                       as away_team_id,
    awayTeam.name                     as away_team_name,
    awayTeam.tla                      as away_team_tla,
    score.winner                      as winner,
    score.duration                    as duration,
    score.fullTime.home               as full_time_home_goals,
    score.fullTime.away               as full_time_away_goals,
    score.halfTime.home               as half_time_home_goals,
    score.halfTime.away               as half_time_away_goals,
    score.extraTime.home              as extra_time_home_goals,
    score.extraTime.away              as extra_time_away_goals,
    score.penalties.home              as penalty_home_goals,
    score.penalties.away              as penalty_away_goals,
    cast(lastUpdated as timestamp)    as last_updated_at,
    extracted_at,
    extraction_date

from source
