-- Every men's World Cup on one comparable scale: the 1930–2022 editions from
-- the historical seed, plus 2026 computed live from this pipeline's own
-- fct_matches — the same goals-per-match calculation applied to both, so the
-- current tournament sits honestly alongside history rather than being pasted
-- in from a different source.
--
-- `is_current` flags the 2026 row for the dashboard; `goals_per_match_rank`
-- ranks editions high-to-low scoring across the whole history including 2026.

with historical as (

    select
        year,
        host,
        winner,
        teams,
        matches,
        goals,
        goals_per_match,
        false as is_current
    from {{ ref('wc_history') }}

),

current_edition as (

    select
        {{ var('current_year', 2026) }}         as year,
        '{{ var("current_host", "USA/Canada/Mexico") }}' as host,
        max(case when stage = 'FINAL' and winner = 'HOME_TEAM' then home_team_name
                 when stage = 'FINAL' and winner = 'AWAY_TEAM' then away_team_name
            end)                                as winner,
        {{ var('expected_teams') }}             as teams,
        count(*)                                as matches,
        -- regulation_*_goals, not full_time_*_goals: the latter includes
        -- penalty-shootout kicks for 4 matches this tournament, which are not
        -- goals by any historical edition's counting convention either.
        sum(regulation_home_goals + regulation_away_goals) as goals,
        round(
            sum(regulation_home_goals + regulation_away_goals) * 1.0 / count(*), 2
        )                                       as goals_per_match,
        true                                    as is_current
    from {{ ref('fct_matches') }}
    where status = 'FINISHED'

),

unioned as (

    select * from historical
    union all
    select * from current_edition

)

select
    year,
    host,
    winner,
    teams,
    cast(matches as integer) as matches,  -- seed integer ∪ count(*) bigint → pin integer
    cast(goals as bigint) as goals,        -- seed bigint ∪ computed hugeint → pin bigint
    goals_per_match,
    is_current,
    cast(
        row_number() over (order by goals_per_match desc, year asc) as integer
    ) as goals_per_match_rank
from unioned
