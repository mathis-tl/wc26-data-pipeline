-- Top scorers of the tournament, latest snapshot, ranked by goals with a
-- deterministic tiebreaker (fewer penalties, then name) so the order is stable.

with latest as (

    select *
    from {{ ref('stg_scorers') }}
    qualify row_number() over (
        partition by player_id
        order by extraction_date desc
    ) = 1

)

select
    row_number() over (
        order by goals desc, penalties asc, assists desc, player_name asc
    )                                   as rank,
    player_id,
    player_name,
    player_nationality,
    team_id,
    team_name,
    team_tla,
    team_crest_url,
    played_matches,
    goals,
    assists,
    penalties
from latest
