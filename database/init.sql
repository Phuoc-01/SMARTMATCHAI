-- database/init.sql
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
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by UUID REFERENCES users(id),
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

-- Vector similarity indexes
CREATE INDEX idx_project_vectors ON projects USING ivfflat (requirement_vector vector_cosine_ops);
CREATE INDEX idx_user_vectors ON users USING ivfflat (skill_vector vector_cosine_ops);