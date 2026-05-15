CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_provider_charge_id_full
  ON payments (provider, provider_charge_id);
