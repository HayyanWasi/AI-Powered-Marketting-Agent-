-- ═══════════════════════════════════════════════════════════════════════════════
-- Migration 027 (Rollback): Revert Execution History Hardening
-- ═══════════════════════════════════════════════════════════════════════════════

DROP POLICY IF EXISTS "Users can access own execution history"
    ON public.execution_history;

CREATE POLICY "Authenticated users can access execution history"
    ON public.execution_history
    FOR ALL
    USING (auth.uid() IS NOT NULL);

DROP INDEX IF EXISTS public.idx_execution_history_user_time;
DROP INDEX IF EXISTS public.idx_execution_history_user_id;

ALTER TABLE public.execution_history
    DROP COLUMN IF EXISTS user_id;
