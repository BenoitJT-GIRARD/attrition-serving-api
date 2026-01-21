-- ===========================
-- Attrition serving - Serving DB Schema
-- ===========================

CREATE TABLE IF NOT EXISTS employees (
  employee_id      INTEGER PRIMARY KEY,
  features         JSONB NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
  id              BIGSERIAL PRIMARY KEY,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  employee_id     INTEGER NULL REFERENCES employees(employee_id),

  input_payload   JSONB NOT NULL,

  proba_depart    DOUBLE PRECISION NOT NULL,
  prediction      SMALLINT NOT NULL,
  threshold       DOUBLE PRECISION NOT NULL,
  model_version   TEXT NOT NULL
);

-- Indexes (important for history endpoints)
CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_employee_id ON predictions(employee_id);
