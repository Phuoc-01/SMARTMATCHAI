-- Add created_at/updated_at columns for BaseModel tables (idempotent)
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

ALTER TABLE projects ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

ALTER TABLE applications ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

ALTER TABLE verified_skills ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;
ALTER TABLE verified_skills ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

ALTER TABLE skills_library ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;
ALTER TABLE skills_library ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

UPDATE users SET created_at = COALESCE(created_at, NOW()), updated_at = COALESCE(updated_at, NOW());
UPDATE projects SET created_at = COALESCE(created_at, NOW()), updated_at = COALESCE(updated_at, NOW());
UPDATE applications SET created_at = COALESCE(created_at, NOW()), updated_at = COALESCE(updated_at, NOW());
UPDATE verified_skills SET created_at = COALESCE(created_at, NOW()), updated_at = COALESCE(updated_at, NOW());
UPDATE skills_library SET created_at = COALESCE(created_at, NOW()), updated_at = COALESCE(updated_at, NOW());
UPDATE audit_log SET created_at = COALESCE(created_at, NOW()), updated_at = COALESCE(updated_at, NOW());
