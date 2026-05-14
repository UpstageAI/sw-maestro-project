UPDATE articles
SET summary = jsonb_build_array(summary #>> '{}')
WHERE summary IS NOT NULL
  AND jsonb_typeof(summary) = 'string';
