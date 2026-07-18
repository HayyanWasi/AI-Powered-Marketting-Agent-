-- Company Profile Service Schema
-- Run this in your Supabase Dashboard SQL Editor

-- 1. Company profiles table
CREATE TABLE IF NOT EXISTS public.company_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL,
    brand_guidelines TEXT NOT NULL,
    brand_tone TEXT,
    reference_image_urls TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_company_profiles_name ON public.company_profiles (company_name);

-- 2. Brand reference images table
CREATE TABLE IF NOT EXISTS public.brand_reference_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_profile_id UUID NOT NULL REFERENCES public.company_profiles(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    uploaded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brand_images_company ON public.brand_reference_images (company_profile_id);

-- 3. Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_company_profiles_updated_at ON public.company_profiles;
CREATE TRIGGER update_company_profiles_updated_at
    BEFORE UPDATE ON public.company_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 4. Create storage bucket (run in Storage section or via this SQL)
-- The bucket 'brand-images' should be created as public via the Storage UI
-- or via the API after tables exist
