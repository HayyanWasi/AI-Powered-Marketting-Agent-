-- ═══════════════════════════════════════════════════════════════════════════════
-- Migration 027: Harden Execution History & Tenant Scoping
-- Rerun-safe creation of execution_history with strict user_id tenant ownership
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. Create execution_history if missing, ensuring user_id is defined
CREATE TABLE IF NOT EXISTS public.execution_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
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

-- 2. Add user_id column if table already existed without it
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'execution_history'
          AND column_name = 'user_id'
    ) THEN
        ALTER TABLE public.execution_history
            ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- 3. Indexes for execution_history query performance and tenant filtering
CREATE INDEX IF NOT EXISTS idx_execution_history_user_id
    ON public.execution_history (user_id);

CREATE INDEX IF NOT EXISTS idx_execution_history_user_time
    ON public.execution_history (user_id, start_time DESC);

CREATE INDEX IF NOT EXISTS idx_execution_history_workflow_id
    ON public.execution_history (workflow_id);

CREATE INDEX IF NOT EXISTS idx_execution_history_status
    ON public.execution_history (status);

CREATE INDEX IF NOT EXISTS idx_execution_history_start_time
    ON public.execution_history (start_time DESC);

CREATE INDEX IF NOT EXISTS idx_execution_history_trace_id
    ON public.execution_history (trace_id);

CREATE INDEX IF NOT EXISTS idx_execution_history_tags
    ON public.execution_history USING GIN (tags);

-- 4. Enable Row Level Security and enforce strict tenant boundary
ALTER TABLE public.execution_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can access execution history"
    ON public.execution_history;

DROP POLICY IF EXISTS "Users can access own execution history"
    ON public.execution_history;

CREATE POLICY "Users can access own execution history"
    ON public.execution_history
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());
