BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS skills TEXT[] DEFAULT '{}';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name IN ('technical_skills', 'soft_skills')
    ) THEN
        UPDATE users
        SET skills = (
            SELECT ARRAY(
                SELECT DISTINCT unnest(
                    COALESCE(users.technical_skills, '{}') || COALESCE(users.soft_skills, '{}')
                )
            )
        )
        WHERE COALESCE(array_length(skills, 1), 0) = 0;
    END IF;
END $$;

ALTER TABLE users DROP COLUMN IF EXISTS technical_skills;
ALTER TABLE users DROP COLUMN IF EXISTS soft_skills;

ALTER TABLE applications ADD COLUMN IF NOT EXISTS match_details JSONB DEFAULT '{}'::jsonb;

COMMIT;
