-- Smart Match AI: PostgreSQL schema with pgvector

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student','lecturer','admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Skills
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Students
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE,
    interests TEXT,
    academic_background TEXT,
    experience TEXT,
    embedding_vector VECTOR(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_students_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Lecturers
CREATE TABLE lecturers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE,
    department TEXT,
    bio TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_lecturers_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lecturer_id UUID NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    requirements TEXT,
    embedding_vector VECTOR(384),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','hidden','locked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_projects_lecturer FOREIGN KEY (lecturer_id) REFERENCES lecturers (id) ON DELETE CASCADE
);

-- Applications
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL,
    project_id UUID NOT NULL,
    match_score NUMERIC(5,2) NOT NULL CHECK (match_score >= 0 AND match_score <= 100),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_applications_student FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    CONSTRAINT fk_applications_project FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT uq_application_student_project UNIQUE (student_id, project_id)
);

-- Student skills m2m
CREATE TABLE student_skills (
    student_id UUID NOT NULL,
    skill_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (student_id, skill_id),
    CONSTRAINT fk_student_skills_student FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    CONSTRAINT fk_student_skills_skill FOREIGN KEY (skill_id) REFERENCES skills (id) ON DELETE CASCADE
);

-- Reports
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reported_user_id UUID NOT NULL,
    reason TEXT NOT NULL,
    content TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','handled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_reports_user FOREIGN KEY (reported_user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_students_user_id ON students (user_id);
CREATE INDEX idx_lecturers_user_id ON lecturers (user_id);
CREATE INDEX idx_projects_lecturer_id ON projects (lecturer_id);
CREATE INDEX idx_applications_student_id ON applications (student_id);
CREATE INDEX idx_applications_project_id ON applications (project_id);
CREATE INDEX idx_applications_match_score ON applications (match_score);
CREATE INDEX idx_student_skills_student_id ON student_skills (student_id);
CREATE INDEX idx_student_skills_skill_id ON student_skills (skill_id);
CREATE INDEX idx_reports_reported_user_id ON reports (reported_user_id);
CREATE INDEX idx_notifications_user_id ON notifications (user_id);
