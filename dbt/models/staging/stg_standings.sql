-- One row per team per extraction_date: official standings snapshots.
-- Used by dim_teams and by the reconciliation test against fct_group_standings.

with source as (

    select * from {{ source('football_data', 'standings') }}

)

select
    team.id                              as team_id,
    team.name                            as team_name,
    team.shortName                       as team_short_name,
    team.tla                             as team_tla,
    team.crest                           as team_crest_url,
    -- standings encode the group as 'Group A'; canonical form is the letter
    replace(standing."group", 'Group ', '') as group_code,
    standing.type                        as standing_type,
    position,
    playedGames                          as played,
    won,
    draw,
    lost,
    points,
    goalsFor                             as goals_for,
    goalsAgainst                         as goals_against,
    goalDifference                       as goal_diff,
    extracted_at,
    extraction_date

from source
