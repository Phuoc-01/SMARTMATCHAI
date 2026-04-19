import uuid
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

db = SQLAlchemy()

VECTOR_DIM = 384
VECTOR_TYPE = Vector(VECTOR_DIM) if Vector else db.PickleType


class BaseModel(db.Model):
    __abstract__ = True
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(BaseModel):
    __tablename__ = 'users'

    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    student_id = db.Column(db.String(50), unique=True, nullable=True)
    faculty = db.Column(db.String(100), nullable=True)
    skills = db.Column(db.ARRAY(db.String), nullable=True)
    research_interests = db.Column(db.ARRAY(db.String), nullable=True)
    year_of_study = db.Column(db.Integer, nullable=True)
    skill_vector = db.Column(VECTOR_TYPE, nullable=False, default=lambda: [0.0] * VECTOR_DIM)
    phone = db.Column(db.String(20))
    gpa = db.Column(db.Numeric(3, 2))
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)

    position = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    research_fields = db.Column(db.ARRAY(db.String), nullable=True)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    #@property
    #def name(self):
    #    return self.full_name

    #@name.setter
    #def name(self, value):
    #    self.full_name = value

    def to_dict(self):
        skill_vector = self.skill_vector
        if skill_vector is None:
            skill_vector = [0.0] * VECTOR_DIM
        elif hasattr(skill_vector, 'tolist'):
            # pgvector may return numpy.ndarray; ensure JSON-serializable
            skill_vector = skill_vector.tolist()

        return {
            'id': str(self.id),
            'full_name': self.full_name,
            'name': self.full_name,
            'email': self.email,
            'role': self.role,
            'student_id': self.student_id,
            'mssv': self.student_id,
            'faculty': self.faculty or '',
            'phone': self.phone or '',
            'gpa': float(self.gpa) if self.gpa else 0.0,
            'year_of_study': self.year_of_study or '',
            'skills': self.skills or [],
            'research_interests': self.research_interests or [],
            'position': self.position,
            'department': self.department,
            'research_fields': self.research_fields or [],
            'skill_vector': skill_vector,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Project(BaseModel):
    __tablename__ = 'projects'

    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=False)
    research_field = db.Column(db.String(100))
    required_skills = db.Column(db.ARRAY(db.String), nullable=True)
    preferred_skills = db.Column(db.ARRAY(db.String), nullable=True)
    difficulty_level = db.Column(db.String(20), default='medium')
    duration_weeks = db.Column(db.Integer)
    max_students = db.Column(db.Integer, default=1)
    requirement_vector = db.Column(VECTOR_TYPE)
    keywords = db.Column(db.ARRAY(db.String), nullable=True)
    status = db.Column(db.String(20), default='open')
    lecturer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    deadline = db.Column(db.Date)
    is_public = db.Column(db.Boolean, default=True)

    lecturer = db.relationship('User', foreign_keys=[lecturer_id])

    def to_dict(self):
        return {
            'id': str(self.id),
            'title': self.title,
            'description': self.description,
            'research_field': self.research_field,
            'required_skills': self.required_skills or [],
            'preferred_skills': self.preferred_skills or [],
            'difficulty_level': self.difficulty_level,
            'max_students': self.max_students,
            'duration_weeks': self.duration_weeks,
            'is_public': self.is_public,
            'status': self.status,
            'lecturer_id': str(self.lecturer_id),
            'lecturer_name': self.lecturer.full_name if self.lecturer else None,
            'deadline': self.deadline.isoformat() if self.deadline else None
        }


class Application(BaseModel):
    __tablename__ = 'applications'

    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.id'), nullable=False)
    match_score = db.Column(db.Numeric(5, 2), default=0)
    match_details = db.Column(db.JSON)
    status = db.Column(db.String(20), default='pending')
    
    application_text = db.Column(db.Text)
    feedback_text = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))

    student = db.relationship('User', foreign_keys=[student_id], backref='student_apps')
    project = db.relationship('Project', foreign_keys=[project_id], backref='project_apps')

    def to_dict(self):
        score = float(self.match_score) if self.match_score else 0
        display_score = round(score if score > 1 else score * 100, 1)

        if display_score >= 70:
            color, label = "#22c55e", "Cao"
        elif display_score >= 30:
            color, label = "#eab308", "Trung bình"
        else:
            color, label = "#ef4444", "Kém"

        return {
            'id': str(self.id),
            'student_id': str(self.student_id),
            'project_id': str(self.project_id),
            'match_score': display_score,
            'match_details': self.match_details or {},
            'match_level': (self.match_details or {}).get('match_level'),
            'match_color': color,
            'match_label': label,
            'status': self.status,
            'application_text': self.application_text or '',
            'feedback_text': self.feedback_text or '',
            'rejection_reason': self.rejection_reason or '',
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by': str(self.reviewed_by) if self.reviewed_by else None,
            'student_name': self.student.full_name if self.student else "N/A",
            'project_title': self.project.title if self.project else "N/A",
            'project_description': self.project.description if self.project else None,
            'required_skills': self.project.required_skills if self.project else [],
            'lecturer_name': self.project.lecturer.full_name if self.project and self.project.lecturer else None
        }



class VerifiedSkill(BaseModel):
    __tablename__ = 'verified_skills'

    # Foreign Keys
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.id'), nullable=True)
    skill = db.Column(db.String(100), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)

    # Optional skill level: beginner, intermediate, expert
    level = db.Column(db.String(50), nullable=True)

    # Verification metadata
    verified_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column('verification_date', db.DateTime, nullable=True)

    # Evidence link (certificate/project)
    evidence = db.Column(db.Text, nullable=True)

    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref=db.backref('verified_skills', lazy='dynamic'))
    verifier = db.relationship('User', foreign_keys=[verified_by])
    project = db.relationship('Project', foreign_keys=[project_id])

    # Ensure each student can only add a skill once
    __table_args__ = (
        db.UniqueConstraint('student_id', 'skill', name='_student_skill_uc'),
    )

    def __repr__(self):
        status = "Verified" if self.is_verified else "Pending"
        return f"<Skill {self.skill} ({status}) - Student: {self.student_id}>"


class ProjectEvaluation(BaseModel):
    __tablename__ = 'project_evaluations'

    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.id'), nullable=False)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    lecturer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)

    score = db.Column(db.Integer, nullable=True)
    note = db.Column(db.Text, nullable=True)

    project = db.relationship('Project', foreign_keys=[project_id])
    student = db.relationship('User', foreign_keys=[student_id])
    lecturer = db.relationship('User', foreign_keys=[lecturer_id])

    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'student_id': str(self.student_id),
            'lecturer_id': str(self.lecturer_id),
            'score': int(self.score) if self.score is not None else None,
            'note': self.note or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ProjectUpdate(BaseModel):
    __tablename__ = 'project_updates'

    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.id'), nullable=False)
    lecturer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)

    content = db.Column(db.Text, nullable=False)

    project = db.relationship('Project', foreign_keys=[project_id])
    lecturer = db.relationship('User', foreign_keys=[lecturer_id])

    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'lecturer_id': str(self.lecturer_id),
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ProjectMilestone(BaseModel):
    __tablename__ = 'project_milestones'

    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)

    project = db.relationship('Project', foreign_keys=[project_id])

    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'title': self.title,
            'description': self.description or '',
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ProjectMilestoneProgress(BaseModel):
    __tablename__ = 'project_milestone_progress'

    milestone_id = db.Column(UUID(as_uuid=True), db.ForeignKey('project_milestones.id'), nullable=False)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    is_done = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    submission_url = db.Column(db.Text, nullable=True)
    submission_note = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=True)

    milestone = db.relationship('ProjectMilestone', foreign_keys=[milestone_id])
    student = db.relationship('User', foreign_keys=[student_id])

    __table_args__ = (
        db.UniqueConstraint('milestone_id', 'student_id', name='_milestone_student_uc'),
    )

    def to_dict(self):
        return {
            'id': str(self.id),
            'milestone_id': str(self.milestone_id),
            'student_id': str(self.student_id),
            'is_done': bool(self.is_done),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'submission_url': self.submission_url or None,
            'submission_note': self.submission_note or None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SkillLibrary(BaseModel):
    __tablename__ = 'skills_library'

    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    related_skills = db.Column(db.ARRAY(db.String), nullable=True, default=list)
    popularity_score = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'related_skills': self.related_skills or [],
            'popularity_score': int(self.popularity_score or 0),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class AuditLog(BaseModel):
    __tablename__ = 'audit_log'

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    user_role = db.Column(db.String(20), nullable=True)

    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(UUID(as_uuid=True), nullable=True)
    entity_name = db.Column(db.String(200), nullable=True)

    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    changed_fields = db.Column(db.ARRAY(db.String), nullable=True)

    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    request_url = db.Column(db.String(500), nullable=True)
    request_method = db.Column(db.String(10), nullable=True)

    severity = db.Column(db.String(20), nullable=False, default='info')

    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id) if self.user_id else None,
            'user_role': self.user_role,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': str(self.entity_id) if self.entity_id else None,
            'entity_name': self.entity_name,
            'old_values': self.old_values or None,
            'new_values': self.new_values or None,
            'changed_fields': self.changed_fields or [],
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_url': self.request_url,
            'request_method': self.request_method,
            'severity': self.severity,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Notification(BaseModel):
    __tablename__ = 'notifications'

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)

    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    data = db.Column(db.JSON, nullable=False, default=dict)

    is_read = db.Column(db.Boolean, nullable=False, default=False)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    priority = db.Column(db.String(20), nullable=False, default='normal')
    delivery_method = db.Column(db.String(20), nullable=False, default='in_app')

    action_url = db.Column(db.String(500), nullable=True)
    action_label = db.Column(db.String(100), nullable=True)
    action_data = db.Column(db.JSON, nullable=False, default=dict)

    scheduled_for = db.Column(db.DateTime, nullable=True)
    read_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'data': self.data or {},
            'is_read': bool(self.is_read),
            'is_archived': bool(self.is_archived),
            'priority': self.priority,
            'delivery_method': self.delivery_method,
            'action_url': self.action_url,
            'action_label': self.action_label,
            'action_data': self.action_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }


class Report(BaseModel):
    __tablename__ = 'reports'

    reporter_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    reported_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)

    reason = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')

    handled_at = db.Column(db.DateTime, nullable=True)
    handled_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)

    reporter = db.relationship('User', foreign_keys=[reporter_id])
    reported_user = db.relationship('User', foreign_keys=[reported_user_id])
    handler = db.relationship('User', foreign_keys=[handled_by])

    def to_dict(self):
        return {
            'id': str(self.id),
            'reporter_id': str(self.reporter_id),
            'reported_user_id': str(self.reported_user_id),
            'reason': self.reason,
            'content': self.content,
            'status': self.status,
            'handled_at': self.handled_at.isoformat() if self.handled_at else None,
            'handled_by': str(self.handled_by) if self.handled_by else None,
            'resolution_notes': self.resolution_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
