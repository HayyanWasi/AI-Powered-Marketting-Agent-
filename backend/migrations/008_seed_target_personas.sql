-- ═══════════════════════════════════════════════════════════════
-- Seed Initial Target Personas
-- Run ONCE before first worker execution.
-- Replace 'YOUR_ACCOUNT_ID' with your actual Unipile account ID.
-- ═══════════════════════════════════════════════════════════════

INSERT INTO public.linkedin_target_personas (account_id, label, search_keywords, max_profiles)
VALUES
    ('YOUR_ACCOUNT_ID', 'AI Founders',        'AI startup founder CEO',             150),
    ('YOUR_ACCOUNT_ID', 'VP of Marketing',     'VP marketing head of marketing',     150),
    ('YOUR_ACCOUNT_ID', 'Tech CTOs',           'CTO chief technology officer tech',  150),
    ('YOUR_ACCOUNT_ID', 'Growth Hackers',      'growth hacker head of growth',       150),
    ('YOUR_ACCOUNT_ID', 'Product Leaders',     'VP product head of product CPO',     150)
ON CONFLICT (account_id, label) DO NOTHING;
