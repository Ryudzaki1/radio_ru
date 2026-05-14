# Database foundation

PostgreSQL is added as an empty persistence layer for the future paid Telegram
question flow. The current radio runtime does not read from or write to the
database yet, so adding this service does not change the live broadcast logic.

## Docker service

`docker-compose.yml` starts `postgres` with:

- database: `POSTGRES_DB` (`radio` by default);
- user: `POSTGRES_USER` (`radio` by default);
- password: `POSTGRES_PASSWORD`;
- persistent volume: `radio-postgres`;
- init scripts: `database/init/*.sql`.

The init scripts run only when the Postgres data volume is created for the
first time. If the volume already exists, schema changes must be applied with a
proper migration command later.

## Initial tables

- `telegram_users` - Telegram listeners and admins.
- `payment_orders` - payable orders before and after Telegram Stars, TON, or
  USDT confirmation.
- `payments` - immutable payment confirmations from the provider.
- `listener_questions` - paid or free listener questions and their lifecycle.
- `audio_assets` - generated mp3 files and their metadata.
- `broadcast_jobs` - future durable queue for voice, music, topic, and listener
  jobs.
- `broadcast_events` - chronological live-air history: live tracks, play
  inserts, voice starts/ends, transitions, broadcast stop/restore events.
- `ai_usage_events` - DeepSeek and ElevenLabs usage accounting.
- `system_events` - audit trail for admin, bot, listener, and system actions.

## Broadcast event relationships

`broadcast_events` is the main table for "what was on air". It stores the
event time, category, title, source file, duration, topic/subtopic text and
metadata.

Optional links are already reserved:

- `listener_question_id` -> `listener_questions.id` for paid listener
  questions.
- `audio_asset_id` -> `audio_assets.id` for generated mp3 files.
- `broadcast_job_id` -> `broadcast_jobs.id` for the future durable queue.

For now, these optional IDs are usually empty because the current broadcast
runtime still uses in-memory queues and JSON files. The table is still useful
immediately because it is filled from the same broadcast events that feed the
admin history.

## Recommended next tables

Add these only when the corresponding feature is implemented:

- `tariffs` - editable prices for questions, urgent questions, and packages.
- `user_balances` - internal prepaid balance if you later sell bundles.
- `refunds` - explicit refund lifecycle for Telegram Stars and crypto payments.
- `moderation_rules` - blocked words, blocked users, and question filters.
- `topic_audio_cache` - normalized cache for topic/subtopic/host combinations
  if the JSON archive becomes too limiting.
- `admin_sessions` - database-backed admin sessions if the current cookie store
  needs to survive restarts across multiple app containers.
