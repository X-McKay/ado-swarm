CREATE TABLE IF NOT EXISTS mission_runs (
  run_id TEXT PRIMARY KEY,
  workflow_id TEXT NOT NULL UNIQUE,
  goal TEXT NOT NULL,
  status TEXT NOT NULL,
  current_plan_version INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS task_events (
  event_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  task_id TEXT,
  event_type TEXT NOT NULL,
  message TEXT NOT NULL,
  state TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
