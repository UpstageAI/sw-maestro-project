DELETE FROM articles
WHERE url LIKE 'https://example.com/%'
   OR id LIKE 'article\_%' ESCAPE '\';
