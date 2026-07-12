{% test row_count_equals(model, value) %}
-- Volumetry guard: fails when the model's row count drifts from the expected
-- value — the project-wide defense against silent row drops.
select
    count(*) as actual_row_count
from {{ model }}
having count(*) != {{ value }}
{% endtest %}
