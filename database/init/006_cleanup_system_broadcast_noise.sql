DELETE FROM system_events
WHERE event IN (
  'topic_cycle_run_started',
  'live_interrupted_for_voice',
  'topic_cycle_fact_queued',
  'voice_audio_start',
  'voice_prelude_start',
  'voice_queued',
  'voice_segment_end',
  'live_music_start',
  'play_music_start',
  'play_queued',
  'music_synced',
  'voice_queue_cleared',
  'broadcast_stopped',
  'broadcast_restored',
  'transition_live_to_play',
  'transition_play_to_live',
  'transition_play_to_play'
);
