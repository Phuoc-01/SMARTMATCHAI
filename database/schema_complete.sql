-- ==================== SMART-MATCH AI DATABASE SCHEMA ====================
-- Production-ready với đầy đủ tính năng

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search

-- ==================== ENUMS ====================
CREATE TYPE user_role AS ENUM ('student', 'lecturer', 'admin');
CREATE TYPE project_status AS ENUM ('draft', 'published', 'in_progress', 'completed', 'cancelled');
CREATE TYPE application_status AS ENUM ('pending', 'reviewing', 'shortlisted', 'accepted', 'rejected', 'withdrawn');
CREATE TYPE skill_level AS ENUM ('beginner', 'intermediate', 'advanced', 'expert');
CREATE TYPE verification_method AS ENUM ('project_completion', 'exam', 'certification', 'lecturer_assessment', 'work_experience');

-- ==================== USERS TABLE ====================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Authentication
    email VARCHAR(255) UNIQUE NOT NULL,
    CONSTRAINT email_must_be_dut CHECK (email ~* '^[A-Za-z0-9._%+-]+@dut\.edu\.vn$'),
    password_hash VARCHAR(255) NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(100),
    reset_token VARCHAR(100),
    reset_token_expires TIMESTAMP,
    
    -- Profile Information
    full_name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    bio TEXT,
    role user_role NOT NULL,
    
    -- Contact Information
    phone VARCHAR(20),
    personal_email VARCHAR(255),
    linkedin_url VARCHAR(500),
    github_url VARCHAR(500),
    portfolio_url VARCHAR(500),
    
    -- Academic Information (Students)
    student_id VARCHAR(50) UNIQUE,
    faculty VARCHAR(100),
    major VARCHAR(100),
    class_code VARCHAR(50),
    gpa DECIMAL(4,2),
    year_of_study INTEGER,
    enrollment_year INTEGER,
    expected_graduation_year INTEGER,
    
    -- Professional Information (Lecturers)
    lecturer_code VARCHAR(50) UNIQUE,
    academic_title VARCHAR(100),
    department VARCHAR(100),
    office_location VARCHAR(200),
    office_hours TEXT,
    research_interests TEXT[] DEFAULT '{}',
    publications JSONB DEFAULT '[]',
    
    -- Skills & AI Vector
    technical_skills TEXT[] DEFAULT '{}',
    soft_skills TEXT[] DEFAULT '{}',
    skill_vector VECTOR(384),
    skill_confidence JSONB DEFAULT '{}', -- {skill: confidence_score}
    
    -- Statistics
    total_projects_completed INTEGER DEFAULT 0,
    avg_project_rating DECIMAL(3,2) DEFAULT 0,
    response_rate DECIMAL(5,2) DEFAULT 0,
    profile_completion_percentage INTEGER DEFAULT 0,
    
    -- Settings & Preferences
    notification_preferences JSONB DEFAULT '{
        "email": true,
        "new_projects": true,
        "application_updates": true,
        "deadline_reminders": true,
        "messages": true
    }',
    privacy_settings JSONB DEFAULT '{
        "profile_visibility": "public",
        "contact_visibility": "verified_only",
        "skills_visibility": "public",
        "grades_visibility": "private"
    }',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    account_status VARCHAR(20) DEFAULT 'active',
    last_login_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_users_email ON users(email),
    INDEX idx_users_role ON users(role),
    INDEX idx_users_faculty ON users(faculty),
    INDEX idx_users_student_id ON users(student_id),
    INDEX idx_users_lecturer_code ON users(lecturer_code),
    INDEX idx_users_skill_vector ON users USING ivfflat (skill_vector vector_cosine_ops)
);

-- ==================== PROJECTS TABLE ====================
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Basic Information
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(600) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    short_description VARCHAR(500),
    thumbnail_url VARCHAR(500),
    
    -- Categorization
    research_field VARCHAR(100),
    sub_field VARCHAR(100),
    project_type VARCHAR(50),
    difficulty_level VARCHAR(20) DEFAULT 'intermediate',
    tags TEXT[] DEFAULT '{}',
    keywords TEXT[] DEFAULT '{}',
    
    -- Requirements
    required_skills TEXT[] DEFAULT '{}',
    preferred_skills TEXT[] DEFAULT '{}',
    requirement_vector VECTOR(384),
    prerequisites TEXT,
    learning_outcomes TEXT[] DEFAULT '{}',
    technical_requirements JSONB DEFAULT '{}',
    
    -- Logistics
    duration_weeks INTEGER,
    time_commitment_hours INTEGER,
    max_students INTEGER DEFAULT 1,
    min_students INTEGER DEFAULT 1,
    is_paid BOOLEAN DEFAULT FALSE,
    stipend_amount DECIMAL(10,2),
    funding_source VARCHAR(200),
    equipment_provided JSONB DEFAULT '[]',
    
    -- Timeline
    start_date DATE,
    end_date DATE,
    application_deadline DATE,
    selection_deadline DATE,
    
    -- Status & Visibility
    status project_status DEFAULT 'draft',
    visibility VARCHAR(20) DEFAULT 'public',
    is_featured BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 0,
    
    -- Metadata
    lecturer_id UUID REFERENCES users(id) ON DELETE CASCADE,
    faculty VARCHAR(100),
    department_id VARCHAR(100),
    
    -- Statistics
    view_count INTEGER DEFAULT 0,
    application_count INTEGER DEFAULT 0,
    save_count INTEGER DEFAULT 0,
    avg_match_score DECIMAL(5,2) DEFAULT 0,
    
    -- SEO & Discovery
    search_vector TSVECTOR,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT valid_dates CHECK (start_date <= end_date),
    CONSTRAINT valid_application_deadline CHECK (application_deadline <= selection_deadline),
    
    -- Indexes
    INDEX idx_projects_status ON projects(status),
    INDEX idx_projects_lecturer ON projects(lecturer_id, status),
    INDEX idx_projects_faculty ON projects(faculty, status),
    INDEX idx_projects_deadline ON projects(application_deadline) WHERE status = 'published',
    INDEX idx_projects_requirement_vector ON projects USING ivfflat (requirement_vector vector_cosine_ops),
    INDEX idx_projects_search_vector ON projects USING gin(search_vector)
);

-- ==================== APPLICATIONS TABLE ====================
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Relations
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    student_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- AI Matching Results
    match_score DECIMAL(5,2) DEFAULT 0,
    match_details JSONB DEFAULT '{}',
    match_breakdown JSONB DEFAULT '{
        "skill_similarity": 0,
        "interest_alignment": 0,
        "experience_relevance": 0,
        "timing_compatibility": 0
    }',
    ranking_position INTEGER,
    
    -- Application Content
    cover_letter TEXT,
    proposal_summary TEXT,
    relevant_experience TEXT,
    motivation_statement TEXT,
    availability_schedule JSONB,
    research_interests_alignment TEXT,
    
    -- Supporting Documents
    resume_url VARCHAR(500),
    transcript_url VARCHAR(500),
    portfolio_url VARCHAR(500),
    recommendation_letters JSONB DEFAULT '[]',
    
    -- Review Process
    status application_status DEFAULT 'pending',
    review_notes TEXT,
    interview_notes TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_to_student TEXT,
    
    -- Timestamps
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    interview_scheduled_at TIMESTAMP WITH TIME ZONE,
    decision_at TIMESTAMP WITH TIME ZONE,
    
    -- Reviewers
    reviewed_by UUID REFERENCES users(id),
    interviewer_id UUID REFERENCES users(id),
    
    -- Constraints & Indexes
    UNIQUE(project_id, student_id),
    INDEX idx_applications_student ON applications(student_id, status),
    INDEX idx_applications_project ON applications(project_id, status),
    INDEX idx_applications_match_score ON applications(match_score DESC),
    INDEX idx_applications_status ON applications(status)
);

-- ==================== SKILLS LIBRARY ====================
CREATE TABLE skills_library (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50),
    description TEXT,
    related_skills TEXT[] DEFAULT '{}',
    popularity_score INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==================== STUDENT SKILLS WITH VERIFICATION ====================
CREATE TABLE student_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID REFERENCES users(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills_library(id) ON DELETE CASCADE,
    
    -- Verification Levels
    verification_level INTEGER NOT NULL CHECK (verification_level IN (1, 2, 3)),
    -- Level 1: Lecturer verified (W=1.0)
    -- Level 2: Evidence uploaded (W=0.7)
    -- Level 3: Self-declared (W=0.4)
    
    -- Verification Details
    verified_by UUID REFERENCES users(id),
    project_id UUID REFERENCES projects(id),
    verification_method verification_method,
    skill_level skill_level,
    confidence_score DECIMAL(3,2) DEFAULT 1.0,
    
    -- Evidence
    evidence_urls TEXT[] DEFAULT '{}',
    evidence_description TEXT,
    verification_criteria JSONB DEFAULT '[]',
    
    -- Assessment
    assessment_date DATE NOT NULL,
    expires_at DATE,
    is_renewable BOOLEAN DEFAULT FALSE,
    
    -- Status
    is_verified BOOLEAN DEFAULT FALSE,
    verification_status VARCHAR(20) DEFAULT 'active',
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints & Indexes
    UNIQUE(student_id, skill_id, verification_level, project_id),
    INDEX idx_student_skills_student ON student_skills(student_id),
    INDEX idx_student_skills_verification ON student_skills(verification_level),
    INDEX idx_student_skills_skill ON student_skills(skill_id)
);

-- ==================== PROJECT COMPLETIONS ====================
CREATE TABLE project_completions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Relations
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    student_id UUID REFERENCES users(id) ON DELETE CASCADE,
    lecturer_id UUID REFERENCES users(id),
    
    -- Completion Details
    completion_date DATE NOT NULL,
    grade VARCHAR(10),
    grade_points DECIMAL(4,2),
    final_report_url VARCHAR(500),
    presentation_url VARCHAR(500),
    code_repository_url VARCHAR(500),
    documentation_url VARCHAR(500),
    
    -- Skills Assessment
    skills_developed JSONB DEFAULT '[]', -- [{skill_id, level, evidence}]
    skills_improved JSONB DEFAULT '[]',
    new_skills_learned JSONB DEFAULT '[]',
    skill_growth_metrics JSONB DEFAULT '{}',
    
    -- Feedback
    student_feedback TEXT,
    lecturer_feedback TEXT,
    peer_feedback JSONB DEFAULT '[]',
    project_outcomes TEXT,
    challenges_faced TEXT,
    lessons_learned TEXT,
    future_recommendations TEXT,
    
    -- Ratings (1-5 scale)
    student_rating INTEGER CHECK (student_rating BETWEEN 1 AND 5),
    lecturer_rating INTEGER CHECK (lecturer_rating BETWEEN 1 AND 5),
    project_rating INTEGER CHECK (project_rating BETWEEN 1 AND 5),
    
    -- Recommendations
    would_recommend BOOLEAN,
    testimonial TEXT,
    is_testimonial_public BOOLEAN DEFAULT FALSE,
    featured BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    completion_certificate_url VARCHAR(500),
    completion_verified BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_project_completions_student ON project_completions(student_id),
    INDEX idx_project_completions_project ON project_completions(project_id),
    UNIQUE(project_id, student_id)
);

-- ==================== NOTIFICATIONS SYSTEM ====================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Recipient
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification Details
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    priority VARCHAR(20) DEFAULT 'normal',
    delivery_method VARCHAR(20) DEFAULT 'in_app', -- in_app, email, both
    
    -- Actions
    action_url VARCHAR(500),
    action_label VARCHAR(100),
    action_data JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Indexes
    INDEX idx_notifications_user ON notifications(user_id, is_read, created_at),
    INDEX idx_notifications_type ON notifications(type, created_at),
    INDEX idx_notifications_priority ON notifications(priority, created_at)
);

-- ==================== MESSAGES ====================
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Thread Management
    conversation_id UUID NOT NULL,
    parent_message_id UUID REFERENCES messages(id),
    
    -- Participants
    sender_id UUID REFERENCES users(id) ON DELETE CASCADE,
    recipient_id UUID REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id),
    
    -- Content
    message_type VARCHAR(20) DEFAULT 'text',
    content TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    is_delivered BOOLEAN DEFAULT FALSE,
    is_edited BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE,
    
    -- Indexes
    INDEX idx_messages_conversation ON messages(conversation_id, created_at),
    INDEX idx_messages_sender ON messages(sender_id, created_at),
    INDEX idx_messages_recipient ON messages(recipient_id, created_at),
    INDEX idx_messages_project ON messages(project_id, created_at)
);

-- ==================== ANALYTICS ====================
CREATE TABLE analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Event Information
    event_type VARCHAR(100) NOT NULL,
    event_name VARCHAR(200) NOT NULL,
    page_url VARCHAR(500),
    referrer_url VARCHAR(500),
    
    -- User Context
    user_id UUID REFERENCES users(id),
    user_role VARCHAR(20),
    session_id VARCHAR(100),
    
    -- Device & Browser
    user_agent TEXT,
    ip_address INET,
    device_type VARCHAR(50),
    browser_name VARCHAR(50),
    os_name VARCHAR(50),
    screen_resolution VARCHAR(20),
    
    -- Event Data
    event_data JSONB DEFAULT '{}',
    event_value DECIMAL(10,2),
    event_duration INTEGER, -- in milliseconds
    
    -- Geolocation
    country VARCHAR(100),
    city VARCHAR(100),
    region VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_analytics_event_type ON analytics(event_type, created_at),
    INDEX idx_analytics_user ON analytics(user_id, created_at),
    INDEX idx_analytics_session ON analytics(session_id, created_at)
);

-- ==================== SYSTEM CONFIGURATION ====================
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    config_type VARCHAR(50) DEFAULT 'string',
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    is_editable BOOLEAN DEFAULT TRUE,
    
    -- Versioning
    version INTEGER DEFAULT 1,
    previous_value JSONB,
    
    -- Metadata
    created_by UUID REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_system_config_key ON system_config(config_key)
);

-- ==================== AUDIT LOG ====================
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Actor
    user_id UUID REFERENCES users(id),
    user_role VARCHAR(20),
    
    -- Action
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    entity_name VARCHAR(200),
    
    -- Changes
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    request_url VARCHAR(500),
    request_method VARCHAR(10),
    
    -- Severity
    severity VARCHAR(20) DEFAULT 'info',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_audit_log_user ON audit_log(user_id, created_at),
    INDEX idx_audit_log_action ON audit_log(action, created_at),
    INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id, created_at)
);

-- ==================== VIEWS ====================
CREATE VIEW student_dashboard_stats AS
SELECT 
    u.id as student_id,
    u.full_name,
    u.student_id as mssv,
    u.faculty,
    u.major,
    u.gpa,
    
    -- Applications
    COUNT(DISTINCT a.id) as total_applications,
    COUNT(DISTINCT CASE WHEN a.status = 'accepted' THEN a.id END) as accepted_applications,
    COUNT(DISTINCT CASE WHEN a.status = 'pending' THEN a.id END) as pending_applications,
    
    -- Projects
    COUNT(DISTINCT pc.id) as completed_projects,
    AVG(pc.project_rating) as avg_project_rating,
    
    -- Skills
    COUNT(DISTINCT ss.id) as total_verified_skills,
    COUNT(DISTINCT CASE WHEN ss.verification_level = 1 THEN ss.id END) as lecturer_verified_skills,
    
    -- Match Scores
    AVG(a.match_score) as avg_match_score,
    MAX(a.match_score) as highest_match_score,
    
    -- Notifications
    COUNT(DISTINCT n.id) as unread_notifications
    
FROM users u
LEFT JOIN applications a ON u.id = a.student_id
LEFT JOIN project_completions pc ON u.id = pc.student_id
LEFT JOIN student_skills ss ON u.id = ss.student_id AND ss.verification_status = 'active'
LEFT JOIN notifications n ON u.id = n.user_id AND n.is_read = FALSE AND n.expires_at > CURRENT_TIMESTAMP
WHERE u.role = 'student'
GROUP BY u.id, u.full_name, u.student_id, u.faculty, u.major, u.gpa;

CREATE VIEW lecturer_dashboard_stats AS
SELECT 
    u.id as lecturer_id,
    u.full_name,
    u.lecturer_code,
    u.department,
    
    -- Projects
    COUNT(DISTINCT p.id) as total_projects,
    COUNT(DISTINCT CASE WHEN p.status = 'published' THEN p.id END) as active_projects,
    COUNT(DISTINCT CASE WHEN p.status = 'in_progress' THEN p.id END) as ongoing_projects,
    COUNT(DISTINCT CASE WHEN p.status = 'completed' THEN p.id END) as completed_projects,
    
    -- Applications
    COUNT(DISTINCT a.id) as total_applications_received,
    COUNT(DISTINCT CASE WHEN a.status = 'pending' THEN a.id END) as pending_applications,
    COUNT(DISTINCT CASE WHEN a.status = 'reviewing' THEN a.id END) as reviewing_applications,
    
    -- Students
    COUNT(DISTINCT a.student_id) as unique_applicants,
    COUNT(DISTINCT pc.student_id) as students_mentored,
    
    -- Skills Verified
    COUNT(DISTINCT ss.id) as skills_verified,
    
    -- Notifications
    COUNT(DISTINCT n.id) as unread_notifications
    
FROM users u
LEFT JOIN projects p ON u.id = p.lecturer_id
LEFT JOIN applications a ON p.id = a.project_id
LEFT JOIN project_completions pc ON u.id = pc.lecturer_id
LEFT JOIN student_skills ss ON u.id = ss.verified_by
LEFT JOIN notifications n ON u.id = n.user_id AND n.is_read = FALSE AND n.expires_at > CURRENT_TIMESTAMP
WHERE u.role = 'lecturer'
GROUP BY u.id, u.full_name, u.lecturer_code, u.department;

-- ==================== FUNCTIONS ====================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION calculate_match_score_with_weights(
    student_vector VECTOR(384),
    project_vector VECTOR(384),
    student_skills TEXT[],
    project_required_skills TEXT[]
)
RETURNS DECIMAL AS $$
DECLARE
    vector_similarity DECIMAL;
    skill_overlap_score DECIMAL;
    final_score DECIMAL;
    matched_skills INTEGER;
    total_required_skills INTEGER;
BEGIN
    -- Calculate vector similarity (0-1)
    IF student_vector IS NOT NULL AND project_vector IS NOT NULL THEN
        vector_similarity := 1 - (student_vector <=> project_vector);
    ELSE
        vector_similarity := 0;
    END IF;
    
    -- Calculate skill overlap
    total_required_skills := COALESCE(array_length(project_required_skills, 1), 0);
    IF total_required_skills > 0 THEN
        SELECT COUNT(*) INTO matched_skills
        FROM unnest(project_required_skills) skill
        WHERE skill = ANY(student_skills);
        
        skill_overlap_score := matched_skills::DECIMAL / total_required_skills;
    ELSE
        skill_overlap_score := 0;
    END IF;
    
    -- Weighted average (70% vector similarity, 30% skill overlap)
    final_score := (vector_similarity * 0.7) + (skill_overlap_score * 0.3);
    
    -- Convert to 0-100 scale
    RETURN final_score * 100;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_project_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(NEW.tags, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ==================== TRIGGERS ====================
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_search_vector 
    BEFORE INSERT OR UPDATE ON projects 
    FOR EACH ROW EXECUTE FUNCTION update_project_search_vector();

CREATE TRIGGER update_applications_updated_at 
    BEFORE UPDATE ON applications 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_student_skills_updated_at 
    BEFORE UPDATE ON student_skills 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_messages_updated_at 
    BEFORE UPDATE ON messages 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at 
    BEFORE UPDATE ON system_config 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==================== INITIAL DATA ====================
-- Insert system configuration
INSERT INTO system_config (config_key, config_value, description) VALUES
('ai_matching_weights', '{"skill_similarity": 0.4, "interest_alignment": 0.25, "experience_relevance": 0.2, "timing_compatibility": 0.15}', 'AI matching algorithm weights'),
('application_settings', '{"default_deadline_days": 30, "max_applications_per_student": 5, "auto_withdraw_after_days": 14}', 'Application system settings'),
('notification_templates', '{"application_submitted": "Your application has been submitted", "match_found": "New project matches your skills"}', 'Notification templates'),
('skill_verification_weights', '{"level_1": 1.0, "level_2": 0.7, "level_3": 0.4}', 'Skill verification level weights'),
('email_settings', '{"smtp_server": "smtp.gmail.com", "smtp_port": 587, "from_email": "noreply@smartmatch.dut.edu.vn"}', 'Email configuration');

-- Insert common skills
INSERT INTO skills_library (name, category) VALUES
('Python', 'Programming'),
('Machine Learning', 'AI/ML'),
('Deep Learning', 'AI/ML'),
('Data Analysis', 'Data Science'),
('Statistics', 'Data Science'),
('SQL', 'Database'),
('PostgreSQL', 'Database'),
('React', 'Frontend'),
('JavaScript', 'Frontend'),
('Node.js', 'Backend'),
('Docker', 'DevOps'),
('Git', 'DevOps'),
('Research Methodology', 'Research'),
('Academic Writing', 'Research'),
('Data Visualization', 'Data Science'),
('TensorFlow', 'AI/ML'),
('PyTorch', 'AI/ML'),
('Computer Vision', 'AI/ML'),
('Natural Language Processing', 'AI/ML'),
('Cloud Computing', 'DevOps');

PRINT '✅ SMART-MATCH AI Database Schema created successfully!';