CREATE UNIQUE INDEX IF NOT EXISTS idx_listener_questions_external_id_full
  ON listener_questions (external_question_id);
