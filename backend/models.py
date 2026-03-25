import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

db = SQLAlchemy()

class BaseModel(db.Model):
    __abstract__ = True
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(db.Model): 
    __tablename__ = 'users'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    
    # Các cột khác giữ nguyên như Adminer
    student_id = db.Column(db.String(50), unique=True, nullable=True)
    faculty = db.Column(db.String(100), nullable=True)
    skills = db.Column(db.ARRAY(db.String), nullable=True)
    research_interests = db.Column(db.ARRAY(db.String), nullable=True)
    year_of_study = db.Column(db.Integer, nullable=True)
    skill_vector = db.Column(Vector(384), nullable=False, default=lambda: [0.0] * 384)
    
    # Lecturer fields
    position = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    research_fields = db.Column(db.ARRAY(db.String), nullable=True)

    # Thêm back_populates để code không bị lỗi khi gọi user.student
    student = db.relationship('Student', uselist=False, back_populates='user')
    lecturer = db.relationship('Lecturer', uselist=False, back_populates='user')
    notifications = db.relationship('Notification', back_populates='user')
    reports = db.relationship('Report', back_populates='reported_user')

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    @property
    def name(self):
        return self.full_name

    @name.setter
    def name(self, value):
        self.full_name = value

    def to_dict(self):
        return {
            'id': str(self.id),
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role,
            'student_id': self.student_id,
            'faculty': self.faculty,
            'skills': self.skills or [],
            'research_interests': self.research_interests or [],
            'year_of_study': self.year_of_study,
            'position': self.position,
            'department': self.department,
            'research_fields': self.research_fields or [],
            'skill_vector': self.skill_vector if self.skill_vector is not None else [0.0] * 384,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Skill(BaseModel):
    __tablename__ = 'skills'
    name = db.Column(db.Text, nullable=False, unique=True)

class Student(BaseModel):
    __tablename__ = 'students'
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    interests = db.Column(db.Text)
    academic_background = db.Column(db.Text)
    experience = db.Column(db.Text)
    embedding_vector = db.Column(Vector(384))
    user = db.relationship('User', back_populates='student')
    applications = db.relationship('Application', back_populates='student', cascade='all, delete-orphan')
    student_skills = db.relationship('StudentSkill', back_populates='student', cascade='all, delete-orphan')
    def to_dict(self):
        return {'id': str(self.id), 'user_id': str(self.user_id), 'interests': self.interests, 'academic_background': self.academic_background, 'experience': self.experience}

class Lecturer(BaseModel):
    __tablename__ = 'lecturers'
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    department = db.Column(db.Text)
    bio = db.Column(db.Text)
    user = db.relationship('User', back_populates='lecturer')
    projects = db.relationship('Project', back_populates='lecturer', cascade='all, delete-orphan')

class Project(BaseModel):
    __tablename__ = 'projects'
    lecturer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('lecturers.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    embedding_vector = db.Column(Vector(384))
    status = db.Column(db.String(20), nullable=False, default='active')
    lecturer = db.relationship('Lecturer', back_populates='projects')
    applications = db.relationship('Application', back_populates='project', cascade='all, delete-orphan')

class Application(BaseModel):
    __tablename__ = 'applications'
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    match_score = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='pending')
    student = db.relationship('Student', back_populates='applications')
    project = db.relationship('Project', back_populates='applications')

class StudentSkill(BaseModel):
    __tablename__ = 'student_skills'
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    skill_id = db.Column(UUID(as_uuid=True), db.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False)
    student = db.relationship('Student', back_populates='student_skills')
    skill = db.relationship('Skill')

class Report(BaseModel):
    __tablename__ = 'reports'
    reported_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='pending')
    reported_user = db.relationship('User', back_populates='reports')

class Notification(BaseModel):
    __tablename__ = 'notifications'
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    user = db.relationship('User', back_populates='notifications')
