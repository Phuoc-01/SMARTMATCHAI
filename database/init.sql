-- database/init.sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    student_id VARCHAR(50) UNIQUE,
    faculty VARCHAR(100),
    phone VARCHAR(20),
    skills TEXT[],
    research_interests TEXT[],
    skill_vector VECTOR(384),
    gpa DECIMAL(3,2),
    year_of_study INTEGER,
    position VARCHAR(100),
    department VARCHAR(100),
    research_fields TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Projects table - ĐÃ SỬA
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    research_field VARCHAR(100),
    required_skills TEXT[],  -- Đã sửa thành TEXT[]
    preferred_skills TEXT[], -- Đã sửa thành TEXT[]
    difficulty_level VARCHAR(20) DEFAULT 'medium',
    duration_weeks INTEGER,
    max_students INTEGER DEFAULT 1,
    requirement_vector VECTOR(384),
    keywords TEXT[],  -- Đã thêm cột này
    status VARCHAR(20) DEFAULT 'open',
    lecturer_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deadline DATE,
    is_public BOOLEAN DEFAULT TRUE
);

-- Applications table
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    match_score DECIMAL(5,2) DEFAULT 0,
    match_details JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    application_text TEXT,
    feedback_text TEXT,
    rejection_reason TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, project_id)
);

-- Verified skills table
CREATE TABLE verified_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES users(id) ON DELETE CASCADE,
    skill VARCHAR(100) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    verified_by UUID REFERENCES users(id),
    project_id UUID,
    verification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evidence TEXT,
    level VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_projects_lecturer_id ON projects(lecturer_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_applications_student_id ON applications(student_id);
CREATE INDEX idx_applications_project_id ON applications(project_id);

-- ==================== PROJECT EVALUATIONS ====================
-- Lecturer evaluates student progress per project over time.
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

CREATE INDEX IF NOT EXISTS idx_project_evaluations_project_student ON project_evaluations(project_id, student_id, created_at);
CREATE INDEX IF NOT EXISTS idx_project_evaluations_lecturer ON project_evaluations(lecturer_id, created_at);

-- ==================== PROJECT UPDATES ====================
CREATE TABLE IF NOT EXISTS project_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    lecturer_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_project_updates_project ON project_updates(project_id, created_at);

-- ==================== PROJECT MILESTONES ====================
CREATE TABLE IF NOT EXISTS project_milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_project_milestones_project ON project_milestones(project_id, created_at);

CREATE TABLE IF NOT EXISTS project_milestone_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    milestone_id UUID REFERENCES project_milestones(id) ON DELETE CASCADE,
    student_id UUID REFERENCES users(id) ON DELETE CASCADE,
    is_done BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    submission_url TEXT,
    submission_note TEXT,
    submitted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(milestone_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_project_milestone_progress_student ON project_milestone_progress(student_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_project_milestone_progress_milestone ON project_milestone_progress(milestone_id, updated_at);

-- ==================== SKILLS LIBRARY ====================
CREATE TABLE IF NOT EXISTS skills_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50),
    description TEXT,
    related_skills TEXT[] DEFAULT '{}',
    popularity_score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_skills_library_name ON skills_library(name);
CREATE INDEX IF NOT EXISTS idx_skills_library_category ON skills_library(category);

-- ==================== NOTIFICATIONS ====================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    data JSONB DEFAULT '{}'::jsonb,
    is_read BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    priority VARCHAR(20) DEFAULT 'normal',
    delivery_method VARCHAR(20) DEFAULT 'in_app',
    action_url VARCHAR(500),
    action_label VARCHAR(100),
    action_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_for TIMESTAMP,
    read_at TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read, created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type, created_at);

-- ==================== AUDIT LOG ====================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    user_role VARCHAR(20),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    entity_name VARCHAR(200),
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_url VARCHAR(500),
    request_method VARCHAR(10),
    severity VARCHAR(20) DEFAULT 'info',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id, created_at);

-- ==================== REPORTS ====================
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID REFERENCES users(id) ON DELETE CASCADE,
    reported_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    content TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    handled_at TIMESTAMP,
    handled_by UUID REFERENCES users(id),
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reports_reported_user ON reports(reported_user_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_reports_reporter ON reports(reporter_id, created_at);

-- Vector similarity indexes
CREATE INDEX idx_project_vectors ON projects USING ivfflat (requirement_vector vector_cosine_ops);
CREATE INDEX idx_user_vectors ON users USING ivfflat (skill_vector vector_cosine_ops);