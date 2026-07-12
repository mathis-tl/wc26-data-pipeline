-- Group standings computed EXCLUSIVELY from fct_matches (never from the
-- standings endpoint — that one is reserved for the reconciliation test).
--
-- FIFA tiebreaker order implemented here:
--   1-3. points DESC, goal difference DESC, goals for DESC
--   4-6. for teams perfectly tied on 1-3: points, goal difference and goals
--        for recomputed on the direct confrontations between the tied teams
--   7.   fair play — NOT AVAILABLE in the football-data.org free tier
--        (documented limitation, see the model YAML)
--   8.   drawing of lots — replaced by a deterministic team_name ASC fallback

with group_matches as (

    select *
    from {{ ref('fct_matches') }}
    where stage = 'GROUP_STAGE'
      and status = 'FINISHED'

),

-- one row per team per match, home and away legs unpivoted
team_match as (

    select
        group_code,
        home_team_id          as team_id,
        home_team_name        as team_name,
        away_team_id          as opponent_id,
        full_time_home_goals  as goals_scored,
        full_time_away_goals  as goals_conceded
    from group_matches

    union all

    select
        group_code,
        away_team_id,
        away_team_name,
        home_team_id,
        full_time_away_goals,
        full_time_home_goals
    from group_matches

),

overall as (

    select
        group_code,
        team_id,
        team_name,
        count(*)                                                        as played,
        sum(case when goals_scored > goals_conceded then 1 else 0 end)  as won,
        sum(case when goals_scored = goals_conceded then 1 else 0 end)  as draw,
        sum(case when goals_scored < goals_conceded then 1 else 0 end)  as lost,
        sum(case when goals_scored > goals_conceded then 3
                 when goals_scored = goals_conceded then 1
                 else 0 end)                                            as points,
        sum(goals_scored)                                               as goals_for,
        sum(goals_conceded)                                             as goals_against,
        sum(goals_scored) - sum(goals_conceded)                         as goal_diff
    from team_match
    group by 1, 2, 3

),

-- teams sharing (points, goal_diff, goals_for) within a group are perfectly
-- tied on criteria 1-3 and need the head-to-head sub-ranking
tied as (

    select
        *,
        count(*) over (
            partition by group_code, points, goal_diff, goals_for
        ) as tie_size
    from overall

),

-- criteria 4-6: same stats, restricted to matches between the tied teams
head_to_head as (

    select
        t.group_code,
        t.team_id,
        sum(case when tm.goals_scored > tm.goals_conceded then 3
                 when tm.goals_scored = tm.goals_conceded then 1
                 else 0 end)                                 as h2h_points,
        sum(tm.goals_scored) - sum(tm.goals_conceded)        as h2h_goal_diff,
        sum(tm.goals_scored)                                 as h2h_goals_for
    from tied t
    join team_match tm
      on tm.group_code = t.group_code
     and tm.team_id = t.team_id
    join tied opp
      on opp.group_code = t.group_code
     and opp.team_id = tm.opponent_id
     and opp.points = t.points
     and opp.goal_diff = t.goal_diff
     and opp.goals_for = t.goals_for
    where t.tie_size > 1
    group by 1, 2

)

select
    t.group_code,
    t.team_id,
    t.team_name,
    t.played,
    t.won,
    t.draw,
    t.lost,
    t.points,
    t.goals_for,
    t.goals_against,
    t.goal_diff,
    row_number() over (
        partition by t.group_code
        order by
            t.points desc,
            t.goal_diff desc,
            t.goals_for desc,
            h.h2h_points desc nulls last,
            h.h2h_goal_diff desc nulls last,
            h.h2h_goals_for desc nulls last,
            t.team_name asc
    ) as position

from tied t
left join head_to_head h
  on h.group_code = t.group_code
 and h.team_id = t.team_id
