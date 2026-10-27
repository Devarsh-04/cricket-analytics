{% macro clean_team(col) %}
coalesce((select team from {{ ref('team_aliases') }} where alias = {{ col }}), {{ col }})
{% endmacro %}

{% macro clean_venue(col) %}
coalesce((select venue from {{ ref('venue_aliases') }} where alias = trim(split_part({{ col }}, ',', 1))), trim(split_part({{ col }}, ',', 1)))
{% endmacro %}
