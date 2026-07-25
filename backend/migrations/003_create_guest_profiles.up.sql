-- Guest Profiles Table
-- Stores researched guest/speaker profiles for reuse across campaigns

CREATE TABLE IF NOT EXISTS public.guest_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    current_position TEXT DEFAULT '',
    organization TEXT DEFAULT '',
    professional_biography TEXT DEFAULT '',
    areas_of_expertise TEXT[] DEFAULT '{}',
    confidence_level TEXT DEFAULT 'LOW' CHECK (confidence_level IN ('HIGH', 'MEDIUM', 'LOW')),
    sources JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for searching by name
CREATE INDEX IF NOT EXISTS idx_guest_profiles_name ON public.guest_profiles (full_name);

-- Unique constraint to prevent duplicate profiles for the same person
CREATE UNIQUE INDEX IF NOT EXISTS idx_guest_profiles_unique_name ON public.guest_profiles (full_name, organization);

-- Auto-update updated_at trigger
CREATE TRIGGER update_guest_profiles_updated_at
    BEFORE UPDATE ON public.guest_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
