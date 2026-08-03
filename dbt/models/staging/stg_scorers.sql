-- One row per scorer per extraction_date: player + team flattened.
-- Snapshot history kept here; the mart picks the latest.

with source as (

    select * from {{ source('football_data', 'scorers') }}

)

select
    player.id                         as player_id,
    player.name                       as player_name,
    player.nationality                as player_nationality,
    player.section                    as player_section,
    team.id                           as team_id,
    team.name                         as team_name,
    team.tla                          as team_tla,
    team.crest                        as team_crest_url,
    playedMatches                     as played_matches,
    goals,
    coalesce(assists, 0)              as assists,
    coalesce(penalties, 0)            as penalties,
    extracted_at,
    extraction_date

from source
