-- End-to-end integrity test of the pipeline.
--
-- The group standings computed from raw match results (fct_group_standings,
-- built exclusively from fct_matches) must match, team by team, the official
-- standings published by football-data.org (stg_standings, latest snapshot).
-- Any team missing on either side, or any divergence in points, goal
-- difference, goals for or position, returns a row — and fails the build.
-- Each returned row carries computed and official values side by side.

with official as (

    select group_code, team_id, team_name, position, points, goal_diff, goals_for
    from {{ ref('stg_standings') }}
    qualify row_number() over (
        partition by team_id
        order by extraction_date desc
    ) = 1

),

computed as (

    select group_code, team_id, team_name, position, points, goal_diff, goals_for
    from {{ ref('fct_group_standings') }}

)

select
    coalesce(c.group_code, o.group_code)  as group_code,
    coalesce(c.team_id, o.team_id)        as team_id,
    coalesce(c.team_name, o.team_name)    as team_name,
    c.position                            as computed_position,
    o.position                            as official_position,
    c.points                              as computed_points,
    o.points                              as official_points,
    c.goal_diff                           as computed_goal_diff,
    o.goal_diff                           as official_goal_diff,
    c.goals_for                           as computed_goals_for,
    o.goals_for                           as official_goals_for

from computed c
full outer join official o
  on c.group_code = o.group_code
 and c.team_id = o.team_id

where c.team_id is null
   or o.team_id is null
   or c.position  != o.position
   or c.points    != o.points
   or c.goal_diff != o.goal_diff
   or c.goals_for != o.goals_for
