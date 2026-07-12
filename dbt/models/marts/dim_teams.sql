-- One row per team, from the latest standings snapshot. Teams seen in
-- matches but absent from standings are kept (with NULL enrichments) so no
-- team can vanish silently on a join.

with standings_latest as (

    select *
    from {{ ref('stg_standings') }}
    qualify row_number() over (
        partition by team_id
        order by extraction_date desc
    ) = 1

),

match_teams as (

    select home_team_id as team_id, home_team_name as team_name, home_team_tla as team_tla
    from {{ ref('int_matches_latest') }}
    where home_team_id is not null

    union

    select away_team_id, away_team_name, away_team_tla
    from {{ ref('int_matches_latest') }}
    where away_team_id is not null

),

missing_from_standings as (

    select mt.team_id, mt.team_name, mt.team_tla
    from match_teams mt
    left join standings_latest s using (team_id)
    where s.team_id is null

)

select
    team_id,
    team_name,
    team_short_name,
    team_tla,
    team_crest_url,
    group_code
from standings_latest

union all

select
    team_id,
    team_name,
    null as team_short_name,
    team_tla,
    null as team_crest_url,
    null as group_code
from missing_from_standings
