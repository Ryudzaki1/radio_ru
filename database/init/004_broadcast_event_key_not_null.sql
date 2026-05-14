UPDATE broadcast_events
SET event_key = encode(digest(
  concat_ws('|',
    event,
    started_at::text,
    coalesce(title, ''),
    coalesce(source_file, ''),
    coalesce(duration_seconds::text, ''),
    coalesce(position_seconds::text, '')
  ),
  'sha256'
), 'hex')
WHERE event_key IS NULL;

ALTER TABLE broadcast_events
  ALTER COLUMN event_key SET NOT NULL;
