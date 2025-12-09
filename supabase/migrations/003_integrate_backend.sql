-- Integration migration for Python backend
-- Adds only essential infrastructure tables: intake_events, intake_queue
-- Minimal changes - does not modify existing tables

-- Intake events table (idempotency tracking)
CREATE TABLE IF NOT EXISTS intake_events (
  event_id TEXT PRIMARY KEY,
  processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on processed_at for cleanup queries
CREATE INDEX IF NOT EXISTS idx_intake_events_processed_at ON intake_events(processed_at DESC);

-- Intake queue table (replaces SQS for processing pipeline)
CREATE TABLE IF NOT EXISTS intake_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  envelope JSONB NOT NULL,
  message_type TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  processed_at TIMESTAMPTZ,
  retry_count INT DEFAULT 0,
  error_message TEXT
);

-- Create indexes for queue processing
CREATE INDEX IF NOT EXISTS idx_intake_queue_processed_at ON intake_queue(processed_at) WHERE processed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_intake_queue_message_type ON intake_queue(message_type);
CREATE INDEX IF NOT EXISTS idx_intake_queue_created_at ON intake_queue(created_at);

-- Enable RLS
ALTER TABLE intake_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE intake_queue ENABLE ROW LEVEL SECURITY;

-- RLS policies for service role
CREATE POLICY "Service role can access all" ON intake_events
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all" ON intake_queue
  FOR ALL USING (auth.role() = 'service_role');

-- Function to get next batch of unprocessed queue items (atomic operation)
CREATE OR REPLACE FUNCTION get_intake_queue_batch(batch_size INT DEFAULT 5)
RETURNS TABLE (
  id UUID,
  envelope JSONB,
  message_type TEXT,
  created_at TIMESTAMPTZ,
  retry_count INT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    iq.id,
    iq.envelope,
    iq.message_type,
    iq.created_at,
    iq.retry_count
  FROM intake_queue iq
  WHERE iq.processed_at IS NULL
  ORDER BY iq.created_at ASC
  LIMIT batch_size
  FOR UPDATE SKIP LOCKED;
END;
$$ LANGUAGE plpgsql;

-- Function to mark queue item as processed
CREATE OR REPLACE FUNCTION mark_intake_queue_processed(
  queue_id UUID,
  error_msg TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
  UPDATE intake_queue
  SET 
    processed_at = NOW(),
    error_message = error_msg
  WHERE id = queue_id;
END;
$$ LANGUAGE plpgsql;

-- Note: audit_log table check - if it doesn't exist, it can be created separately
-- We're keeping this migration minimal and focused on intake pipeline only

