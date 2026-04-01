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
            color, label = "#eab308", "Trung binh"
        else:
            color, label = "#ef4444", "Kem"

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

    def verify(self, admin_id):
        self.is_verified = True
        self.verified_by = admin_id
        from datetime import datetime
        self.verified_at = datetime.utcnow()

    def to_dict(self):
        return {
            'id': str(self.id),
            'student_id': str(self.student_id),
            'project_id': str(self.project_id) if self.project_id else None,
            'skill': self.skill,
            'level': self.level,
            'is_verified': bool(self.is_verified),
            'verified_by': str(self.verified_by) if self.verified_by else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'evidence': self.evidence,
        }


class SkillLibrary(BaseModel):
    __tablename__ = 'skills_library'

    name = db.Column(db.String(100), unique=True, nullable=False)


class AuditLog(BaseModel):
    __tablename__ = 'audit_log'

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)

    user = db.relationship('User', foreign_keys=[user_id])
