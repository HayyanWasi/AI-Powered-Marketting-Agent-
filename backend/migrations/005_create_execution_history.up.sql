-- Execution History Table
-- Searchable record of completed workflow executions, written by
-- PlatformOperationsService.record_execution_complete().
-- Column set must stay in sync with ExecutionHistoryRecord.to_dict().

CREATE TABLE IF NOT EXISTS public.execution_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id TEXT NOT NULL,
    workflow_type TEXT DEFAULT '',
    status TEXT NOT NULL,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    duration_ms INTEGER DEFAULT 0,
    total_cost_usd NUMERIC(12, 6) DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    trace_id UUID,
    guardrail_summary JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Filters used by ExecutionHistoryRepository.query()
CREATE INDEX IF NOT EXISTS idx_execution_history_workflow_id ON public.execution_history (workflow_id);
CREATE INDEX IF NOT EXISTS idx_execution_history_status ON public.execution_history (status);
CREATE INDEX IF NOT EXISTS idx_execution_history_start_time ON public.execution_history (start_time DESC);
CREATE INDEX IF NOT EXISTS idx_execution_history_trace_id ON public.execution_history (trace_id);

-- Tag containment filter (.contains on tags)
CREATE INDEX IF NOT EXISTS idx_execution_history_tags ON public.execution_history USING GIN (tags);
