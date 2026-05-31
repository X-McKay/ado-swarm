CREATE TABLE IF NOT EXISTS run_artifacts (
  artifact_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  task_id TEXT,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  uri TEXT,
  content JSONB NOT NULL DEFAULT '{}'::jsonb,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_run_artifacts_run_id ON run_artifacts(run_id);

CREATE TABLE IF NOT EXISTS agent_checkpoints (
  checkpoint_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  position TEXT NOT NULL,
  cycle_index INTEGER NOT NULL DEFAULT 0,
  checkpoint JSONB NOT NULL DEFAULT '{}'::jsonb,
  app_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  schema_version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_agent_checkpoints_task ON agent_checkpoints(run_id, task_id);

CREATE TABLE IF NOT EXISTS budget_events (
  event_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  task_id TEXT,
  policy JSONB NOT NULL DEFAULT '{}'::jsonb,
  usage JSONB NOT NULL DEFAULT '{}'::jsonb,
  accepted_outcome BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_budget_events_run_id ON budget_events(run_id);
