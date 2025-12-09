-- Missing tables migration
-- Creates tables referenced by backend code but missing from previous migrations

-- Classifications table (audit trail for message classifications)
CREATE TABLE IF NOT EXISTS classifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id TEXT,
  user_id TEXT,
  channel_id TEXT,
  message_ts TEXT,
  message TEXT,
  classification JSONB NOT NULL,
  message_type TEXT,
  group_key TEXT,
  task_key TEXT,
  assignee_hint TEXT,
  due_date DATE,
  confidence FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for classifications
CREATE INDEX IF NOT EXISTS idx_classifications_event_id ON classifications(event_id);
CREATE INDEX IF NOT EXISTS idx_classifications_user_id ON classifications(user_id);
CREATE INDEX IF NOT EXISTS idx_classifications_channel_id ON classifications(channel_id);
CREATE INDEX IF NOT EXISTS idx_classifications_message_type ON classifications(message_type);
CREATE INDEX IF NOT EXISTS idx_classifications_created_at ON classifications(created_at DESC);

-- Realtors table (if it doesn't exist - primary people/user table)
CREATE TABLE IF NOT EXISTS realtors (
  realtor_id TEXT PRIMARY KEY,
  slack_user_id TEXT UNIQUE,
  name TEXT,
  email TEXT,
  status TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for realtors
CREATE INDEX IF NOT EXISTS idx_realtors_slack_user_id ON realtors(slack_user_id);
CREATE INDEX IF NOT EXISTS idx_realtors_status ON realtors(status);

-- Agent tasks table (if it doesn't exist - tasks not tied to listings)
CREATE TABLE IF NOT EXISTS agent_tasks (
  task_id TEXT PRIMARY KEY,
  realtor_id TEXT,
  task_key TEXT,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'OPEN',
  task_category TEXT,
  priority INT DEFAULT 0,
  due_date DATE,
  inputs JSONB DEFAULT '{}'::jsonb,
  deleted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for agent_tasks
CREATE INDEX IF NOT EXISTS idx_agent_tasks_realtor_id ON agent_tasks(realtor_id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks(status);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_deleted_at ON agent_tasks(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_agent_tasks_task_key ON agent_tasks(task_key);

-- Enable RLS
ALTER TABLE classifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE realtors ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_tasks ENABLE ROW LEVEL SECURITY;

-- RLS policies for service role
CREATE POLICY "Service role can access all" ON classifications
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all" ON realtors
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all" ON agent_tasks
  FOR ALL USING (auth.role() = 'service_role');


