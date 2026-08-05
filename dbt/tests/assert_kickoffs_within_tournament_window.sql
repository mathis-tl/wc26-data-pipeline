-- Every match must kick off inside the edition's window (vars in
-- dbt_project.yml). A row outside the window means either corrupt source
-- data or edition vars that no longer match the data being built.

select
    match_id,
    kickoff_at
from {{ ref('fct_matches') }}
where kickoff_at < cast('{{ var("tournament_start") }}' as timestamp)
   or kickoff_at >= cast('{{ var("tournament_end") }}' as timestamp) + interval 1 day
