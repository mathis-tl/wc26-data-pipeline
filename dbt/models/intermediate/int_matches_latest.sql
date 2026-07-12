-- Latest snapshot of every match: staging keeps the full snapshot history,
-- this model is the single place where "latest wins" is decided, so the
-- marts never re-implement it.

select *
from {{ ref('stg_matches') }}
qualify row_number() over (
    partition by match_id
    order by extraction_date desc
) = 1
