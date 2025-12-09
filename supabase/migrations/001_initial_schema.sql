-- Initial schema for ArchieOS Backend
-- Core tables: people, listings, tasks, audit_log

-- People table (Slack user resolution)
CREATE TABLE IF NOT EXISTS people (
  person_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT,
  slack_user_id TEXT UNIQUE,
  role TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on slack_user_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_people_slack_user_id ON people(slack_user_id);

-- Listings table
CREATE TABLE IF NOT EXISTS listings (
  listing_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type TEXT CHECK (type IN ('SALE', 'LEASE') OR type IS NULL),
  status TEXT DEFAULT 'new',
  address_string TEXT,
  agent_id UUID REFERENCES people(person_id) ON DELETE SET NULL,
  due_date DATE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on agent_id for queries
CREATE INDEX IF NOT EXISTS idx_listings_agent_id ON listings(agent_id);
CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
  task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id UUID REFERENCES listings(listing_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  status TEXT DEFAULT 'OPEN',
  task_def_id TEXT,
  is_stray BOOLEAN DEFAULT FALSE,
  task_category TEXT,
  inputs JSONB DEFAULT '{}'::jsonb,
  agent_id UUID REFERENCES people(person_id) ON DELETE SET NULL,
  agent TEXT,
  due_date DATE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tasks_listing_id ON tasks(listing_id);
CREATE INDEX IF NOT EXISTS idx_tasks_is_stray ON tasks(is_stray);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent_id ON tasks(agent_id);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  content TEXT,
  performed_by TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for entity_type and action queries
CREATE INDEX IF NOT EXISTS idx_audit_log_entity_type_action ON audit_log(entity_type, action);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);

-- Enable Row Level Security (RLS) - basic policies
ALTER TABLE people ENABLE ROW LEVEL SECURITY;
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (can be refined based on auth requirements)
-- For now, allow service role to access everything
CREATE POLICY "Service role can access all" ON people
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all" ON listings
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all" ON tasks
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all" ON audit_log
  FOR ALL USING (auth.role() = 'service_role');

