-- Canonical swarm_runs schema for fresh installs and upgrades; ringer.py never creates this table itself.

CREATE TABLE IF NOT EXISTS swarm_runs (
    id bigserial PRIMARY KEY,
    logged_at timestamptz NOT NULL DEFAULT now(),
    run_id text,
    pattern text,
    task_key text,
    spec text,
    worker_engine text,
    shepherd_model text,
    verify_method text,
    verdict text,
    duration_ms bigint,
    worker_tokens bigint,
    notes text,
    orchestrator text,
    model text,
    reported_model text,
    expected_model text,
    reasoning_effort text,
    task_type text,
    retry boolean,
    payload jsonb
);

ALTER TABLE swarm_runs ADD COLUMN IF NOT EXISTS model text;
ALTER TABLE swarm_runs ADD COLUMN IF NOT EXISTS reported_model text;
ALTER TABLE swarm_runs ADD COLUMN IF NOT EXISTS expected_model text;
ALTER TABLE swarm_runs ADD COLUMN IF NOT EXISTS reasoning_effort text;
ALTER TABLE swarm_runs ADD COLUMN IF NOT EXISTS task_type text;
ALTER TABLE swarm_runs ADD COLUMN IF NOT EXISTS retry boolean;
ALTER TABLE swarm_runs ADD COLUMN IF NOT EXISTS payload jsonb;
