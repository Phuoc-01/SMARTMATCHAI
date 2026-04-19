-- Add submission fields to milestone progress (idempotent)

ALTER TABLE IF EXISTS project_milestone_progress
    ADD COLUMN IF NOT EXISTS submission_url TEXT;

ALTER TABLE IF EXISTS project_milestone_progress
    ADD COLUMN IF NOT EXISTS submission_note TEXT;

ALTER TABLE IF EXISTS project_milestone_progress
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP;
