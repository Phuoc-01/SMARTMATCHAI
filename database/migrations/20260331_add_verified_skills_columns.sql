-- Add missing columns to verified_skills (idempotent)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'verified_skills'
          AND column_name = 'evidence_url'
    ) THEN
        ALTER TABLE verified_skills RENAME COLUMN evidence_url TO evidence;
    END IF;
END $$;

ALTER TABLE verified_skills ADD COLUMN IF NOT EXISTS project_id UUID;
ALTER TABLE verified_skills ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE verified_skills ADD COLUMN IF NOT EXISTS verification_date TIMESTAMP;
ALTER TABLE verified_skills ADD COLUMN IF NOT EXISTS evidence TEXT;

-- Optional: backfill verification_date from verified_at if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'verified_skills'
          AND column_name = 'verified_at'
    ) THEN
        EXECUTE 'UPDATE verified_skills SET verification_date = verified_at WHERE verification_date IS NULL';
    END IF;
END $$;
