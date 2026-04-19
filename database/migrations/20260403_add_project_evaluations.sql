-- Add project evaluations for lecturer to track student progress
-- Idempotent migration for existing databases

CREATE TABLE IF NOT EXISTS project_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    student_id UUID REFERENCES users(id) ON DELETE CASCADE,
    lecturer_id UUID REFERENCES users(id) ON DELETE CASCADE,
    score INTEGER,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_project_evaluations_project_student
    ON project_evaluations(project_id, student_id, created_at);

CREATE INDEX IF NOT EXISTS idx_project_evaluations_lecturer
    ON project_evaluations(lecturer_id, created_at);
