BEGIN;

-- Ensure UUID generation function exists (init.sql already uses gen_random_uuid())
CREATE EXTENSION IF NOT EXISTS pgcrypto;

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

ALTER TABLE skills_library ADD COLUMN IF NOT EXISTS category VARCHAR(50);
ALTER TABLE skills_library ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE skills_library ADD COLUMN IF NOT EXISTS related_skills TEXT[] DEFAULT '{}';
ALTER TABLE skills_library ADD COLUMN IF NOT EXISTS popularity_score INTEGER DEFAULT 0;
ALTER TABLE skills_library ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE skills_library ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

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

ALTER TABLE notifications ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS type VARCHAR(50);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS title VARCHAR(200);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS message TEXT;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS data JSONB DEFAULT '{}'::jsonb;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'normal';
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS delivery_method VARCHAR(20) DEFAULT 'in_app';
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS action_url VARCHAR(500);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS action_label VARCHAR(100);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS action_data JSONB DEFAULT '{}'::jsonb;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMP;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS read_at TIMESTAMP;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_name = 'notifications'
          AND constraint_type = 'FOREIGN KEY'
          AND constraint_name = 'fk_notifications_user'
    ) THEN
        ALTER TABLE notifications
            ADD CONSTRAINT fk_notifications_user
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    END IF;
END $$;

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

ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS user_role VARCHAR(20);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS entity_type VARCHAR(50);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS entity_id UUID;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS entity_name VARCHAR(200);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS old_values JSONB;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS new_values JSONB;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS changed_fields TEXT[];
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS ip_address VARCHAR(45);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS user_agent TEXT;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS request_url VARCHAR(500);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS request_method VARCHAR(10);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'info';
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

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

ALTER TABLE reports ADD COLUMN IF NOT EXISTS reporter_id UUID;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS reported_user_id UUID;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS reason TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS content TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS handled_at TIMESTAMP;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS handled_by UUID;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS resolution_notes TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_name = 'reports'
          AND constraint_type = 'FOREIGN KEY'
          AND constraint_name = 'fk_reports_reporter'
    ) THEN
        ALTER TABLE reports
            ADD CONSTRAINT fk_reports_reporter
            FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_name = 'reports'
          AND constraint_type = 'FOREIGN KEY'
          AND constraint_name = 'fk_reports_reported_user'
    ) THEN
        ALTER TABLE reports
            ADD CONSTRAINT fk_reports_reported_user
            FOREIGN KEY (reported_user_id) REFERENCES users(id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_reports_reported_user ON reports(reported_user_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_reports_reporter ON reports(reporter_id, created_at);

COMMIT;
