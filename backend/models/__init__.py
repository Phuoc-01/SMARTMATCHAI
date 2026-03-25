"""
SQLAlchemy Models for SMART-MATCH AI
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Dict, Any

from sqlalchemy import Column, String, Text, Boolean, Integer, Float, Date, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB, ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

# ==================== ENUMS ====================
class UserRole(str, PyEnum):
    STUDENT = "student"
    LECTURER = "lecturer"
    ADMIN = "admin"

class ProjectStatus(str, PyEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ApplicationStatus(str, PyEnum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    SHORTLISTED = "shortlisted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class SkillLevel(str, PyEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class VerificationMethod(str, PyEnum):
    PROJECT_COMPLETION = "project_completion"
    EXAM = "exam"
    CERTIFICATION = "certification"
    LECTURER_ASSESSMENT = "lecturer_assessment"
    WORK_EXPERIENCE = "work_experience"

# ==================== MIXINS ====================
class TimestampMixin:
    """Mixin for timestamp fields"""
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime(timezone=True))

# ==================== USER MODEL ====================
class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(100))
    reset_token = Column(String(100))
    reset_token_expires = Column(DateTime(timezone=True))
    
    # Profile Information
    full_name = Column(String(255), nullable=False)
    avatar_url = Column(String(500))
    bio = Column(Text)
    role = Column(String(20), nullable=False)  # Using String for flexibility
    
    # Contact Information
    phone = Column(String(20))
    personal_email = Column(String(255))
    linkedin_url = Column(String(500))
    github_url = Column(String(500))
    portfolio_url = Column(String(500))
    
    # Academic Information (Students)
    student_id = Column(String(50), unique=True, index=True)
    faculty = Column(String(100), index=True)
    major = Column(String(100))
    class_code = Column(String(50))
    gpa = Column(Float)  # Using Float instead of Decimal for simplicity
    year_of_study = Column(Integer)
    enrollment_year = Column(Integer)
    expected_graduation_year = Column(Integer)
    
    # Professional Information (Lecturers)
    lecturer_code = Column(String(50), unique=True, index=True)
    academic_title = Column(String(100))
    department = Column(String(100))
    office_location = Column(String(200))
    office_hours = Column(Text)
    research_interests = Column(ARRAY(String), default=list)
    publications = Column(JSONB, default=list)
    
    # Skills & AI Vector
    technical_skills = Column(ARRAY(String), default=list)
    soft_skills = Column(ARRAY(String), default=list)
    skill_vector = Column(Vector(384))
    skill_confidence = Column(JSONB, default=dict)
    
    # Statistics
    total_projects_completed = Column(Integer, default=0)
    avg_project_rating = Column(Float, default=0.0)
    response_rate = Column(Float, default=0.0)
    profile_completion_percentage = Column(Integer, default=0)
    
    # Settings & Preferences
    notification_preferences = Column(JSONB, default={
        "email": True,
        "new_projects": True,
        "application_updates": True,
        "deadline_reminders": True,
        "messages": True
    })
    privacy_settings = Column(JSONB, default={
        "profile_visibility": "public",
        "contact_visibility": "verified_only",
        "skills_visibility": "public",
        "grades_visibility": "private"
    })
    
    # Status
    is_verified = Column(Boolean, default=False, nullable=False)
    account_status = Column(String(20), default="active")
    last_login_at = Column(DateTime(timezone=True))
    
    # Relationships
    projects = relationship("Project", back_populates="lecturer", foreign_keys="Project.lecturer_id")
    applications = relationship("Application", back_populates="student", foreign_keys="Application.student_id")
    verified_skills = relationship("StudentSkill", back_populates="student", foreign_keys="StudentSkill.student_id")
    sent_messages = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")
    received_messages = relationship("Message", back_populates="recipient", foreign_keys="Message.recipient_id")
    notifications = relationship("Notification", back_populates="user")
    skill_verifications = relationship("StudentSkill", back_populates="verifier", foreign_keys="StudentSkill.verified_by")
    
    # Validations
    @validates('email')
    def validate_email(self, key, email):
        if not email.endswith('@dut.edu.vn'):
            raise ValueError('Email must be a DUT email address')
        return email
    
    @validates('gpa')
    def validate_gpa(self, key, gpa):
        if gpa is not None and (gpa < 0 or gpa > 4):
            raise ValueError('GPA must be between 0 and 4')
        return gpa
    
    def set_password(self, password: str):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert user to dictionary for API response"""
        data = {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "faculty": self.faculty,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
        
        # Role-specific fields
        if self.role == UserRole.STUDENT.value:
            data.update({
                "student_id": self.student_id,
                "class": self.class_code,
                "major": self.major,
                "gpa": self.gpa,
                "year_of_study": self.year_of_study,
                "technical_skills": self.technical_skills,
                "soft_skills": self.soft_skills,
                "total_projects_completed": self.total_projects_completed,
                "avg_project_rating": self.avg_project_rating,
                "profile_completion_percentage": self.profile_completion_percentage,
            })
        elif self.role == UserRole.LECTURER.value:
            data.update({
                "lecturer_code": self.lecturer_code,
                "academic_title": self.academic_title,
                "department": self.department,
                "office_location": self.office_location,
                "office_hours": self.office_hours,
                "research_interests": self.research_interests,
            })
        
        return data
    
    def get_role_display(self) -> str:
        """Get display name for role"""
        role_display = {
            UserRole.STUDENT.value: "Sinh viên",
            UserRole.LECTURER.value: "Giảng viên",
            UserRole.ADMIN.value: "Quản trị viên"
        }
        return role_display.get(self.role, self.role)
    
    def calculate_profile_completion(self) -> int:
        """Calculate profile completion percentage"""
        fields = [
            self.full_name, self.email, self.faculty,
            self.avatar_url, self.bio
        ]
        
        if self.role == UserRole.STUDENT.value:
            fields.extend([self.student_id, self.major, self.class_code])
            if self.technical_skills:
                fields.append(True)
        elif self.role == UserRole.LECTURER.value:
            fields.extend([self.lecturer_code, self.department, self.academic_title])
            if self.research_interests:
                fields.append(True)
        
        completed_fields = sum(1 for field in fields if field)
        total_fields = len(fields)
        
        return int((completed_fields / total_fields) * 100) if total_fields > 0 else 0

# ==================== PROJECT MODEL ====================
class Project(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(600), unique=True, nullable=False, index=True)
    
    # Basic Information
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    short_description = Column(String(500))
    thumbnail_url = Column(String(500))
    
    # Categorization
    research_field = Column(String(100))
    sub_field = Column(String(100))
    project_type = Column(String(50))
    difficulty_level = Column(String(20), default="intermediate")
    tags = Column(ARRAY(String), default=list)
    keywords = Column(ARRAY(String), default=list)
    
    # Requirements
    required_skills = Column(ARRAY(String), default=list)
    preferred_skills = Column(ARRAY(String), default=list)
    requirement_vector = Column(Vector(384))
    prerequisites = Column(Text)
    learning_outcomes = Column(ARRAY(String), default=list)
    technical_requirements = Column(JSONB, default=dict)
    
    # Logistics
    duration_weeks = Column(Integer)
    time_commitment_hours = Column(Integer)
    max_students = Column(Integer, default=1)
    min_students = Column(Integer, default=1)
    is_paid = Column(Boolean, default=False)
    stipend_amount = Column(Float)
    funding_source = Column(String(200))
    equipment_provided = Column(JSONB, default=list)
    
    # Timeline
    start_date = Column(Date)
    end_date = Column(Date)
    application_deadline = Column(Date, index=True)
    selection_deadline = Column(Date)
    
    # Status & Visibility
    status = Column(String(20), default=ProjectStatus.DRAFT.value, index=True)
    visibility = Column(String(20), default="public")
    is_featured = Column(Boolean, default=False)
    priority = Column(Integer, default=0)
    
    # Metadata
    lecturer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    faculty = Column(String(100), index=True)
    department_id = Column(String(100))
    
    # Statistics
    view_count = Column(Integer, default=0)
    application_count = Column(Integer, default=0)
    save_count = Column(Integer, default=0)
    avg_match_score = Column(Float, default=0.0)
    
    # SEO & Discovery
    search_vector = Column(Text)  # Simplified for SQLAlchemy
    
    # Timestamps for status changes
    published_at = Column(DateTime(timezone=True))
    archived_at = Column(DateTime(timezone=True))
    
    # Relationships
    lecturer = relationship("User", back_populates="projects", foreign_keys=[lecturer_id])
    applications = relationship("Application", back_populates="project", cascade="all, delete-orphan")
    completions = relationship("ProjectCompletion", back_populates="project", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="project")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('start_date <= end_date', name='valid_dates'),
        CheckConstraint('application_deadline <= selection_deadline', name='valid_application_deadline'),
    )
    
    @validates('max_students', 'min_students')
    def validate_student_counts(self, key, value):
        if value < 1:
            raise ValueError(f'{key} must be at least 1')
        return value
    
    def to_dict(self, include_applications: bool = False) -> Dict[str, Any]:
        """Convert project to dictionary for API response"""
        data = {
            "id": str(self.id),
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "short_description": self.short_description,
            "thumbnail_url": self.thumbnail_url,
            "research_field": self.research_field,
            "sub_field": self.sub_field,
            "project_type": self.project_type,
            "difficulty_level": self.difficulty_level,
            "tags": self.tags,
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "duration_weeks": self.duration_weeks,
            "time_commitment_hours": self.time_commitment_hours,
            "max_students": self.max_students,
            "min_students": self.min_students,
            "is_paid": self.is_paid,
            "stipend_amount": self.stipend_amount,
            "funding_source": self.funding_source,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "application_deadline": self.application_deadline.isoformat() if self.application_deadline else None,
            "selection_deadline": self.selection_deadline.isoformat() if self.selection_deadline else None,
            "status": self.status,
            "visibility": self.visibility,
            "is_featured": self.is_featured,
            "faculty": self.faculty,
            "view_count": self.view_count,
            "application_count": self.application_count,
            "save_count": self.save_count,
            "avg_match_score": self.avg_match_score,
            "lecturer": self.lecturer.to_dict() if self.lecturer else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "days_until_deadline": self.get_days_until_deadline(),
            "is_accepting_applications": self.is_accepting_applications(),
        }
        
        if include_applications and self.applications:
            data["applications"] = [app.to_dict() for app in self.applications]
        
        return data
    
    def get_status_display(self) -> str:
        """Get display name for status"""
        status_display = {
            ProjectStatus.DRAFT.value: "Bản nháp",
            ProjectStatus.PUBLISHED.value: "Đang tuyển",
            ProjectStatus.IN_PROGRESS.value: "Đang thực hiện",
            ProjectStatus.COMPLETED.value: "Đã hoàn thành",
            ProjectStatus.CANCELLED.value: "Đã hủy"
        }
        return status_display.get(self.status, self.status)
    
    def is_accepting_applications(self) -> bool:
        """Check if project is accepting applications"""
        if self.status != ProjectStatus.PUBLISHED.value:
            return False
        
        if self.application_deadline and self.application_deadline < datetime.now().date():
            return False
        
        if self.application_count >= self.max_students:
            return False
        
        return True
    
    def get_days_until_deadline(self) -> int:
        """Get days remaining until deadline"""
        if not self.application_deadline:
            return None
        
        from datetime import date
        delta = (self.application_deadline - date.today()).days
        return delta if delta >= 0 else None
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
    
    def increment_application_count(self):
        """Increment application count"""
        self.application_count += 1

# ==================== APPLICATION MODEL ====================
class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relations
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # AI Matching Results
    match_score = Column(Float, default=0.0, index=True)
    match_details = Column(JSONB, default=dict)
    match_breakdown = Column(JSONB, default={
        "skill_similarity": 0.0,
        "interest_alignment": 0.0,
        "experience_relevance": 0.0,
        "timing_compatibility": 0.0
    })
    ranking_position = Column(Integer)
    
    # Application Content
    cover_letter = Column(Text)
    proposal_summary = Column(Text)
    relevant_experience = Column(Text)
    motivation_statement = Column(Text)
    availability_schedule = Column(JSONB, default=dict)
    research_interests_alignment = Column(Text)
    
    # Supporting Documents
    resume_url = Column(String(500))
    transcript_url = Column(String(500))
    portfolio_url = Column(String(500))
    recommendation_letters = Column(JSONB, default=list)
    
    # Review Process
    status = Column(String(20), default=ApplicationStatus.PENDING.value, index=True)
    review_notes = Column(Text)
    interview_notes = Column(Text)
    rating = Column(Integer)
    feedback_to_student = Column(Text)
    
    # Timestamps
    applied_at = Column(DateTime(timezone=True), default=func.now())
    reviewed_at = Column(DateTime(timezone=True))
    interview_scheduled_at = Column(DateTime(timezone=True))
    decision_at = Column(DateTime(timezone=True))
    
    # Reviewers
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    interviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    project = relationship("Project", back_populates="applications")
    student = relationship("User", back_populates="applications", foreign_keys=[student_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    interviewer = relationship("User", foreign_keys=[interviewer_id])
    
    # Constraints
    __table_args__ = (
        CheckConstraint('rating IS NULL OR (rating >= 1 AND rating <= 5)', name='valid_rating'),
    )
    
    @validates('match_score')
    def validate_match_score(self, key, score):
        if score is not None and (score < 0 or score > 100):
            raise ValueError('Match score must be between 0 and 100')
        return score
    
    def to_dict(self, include_student: bool = True, include_project: bool = True) -> Dict[str, Any]:
        """Convert application to dictionary for API response"""
        data = {
            "id": str(self.id),
            "match_score": self.match_score,
            "match_details": self.match_details,
            "match_breakdown": self.match_breakdown,
            "cover_letter": self.cover_letter,
            "proposal_summary": self.proposal_summary,
            "status": self.status,
            "status_display": self.get_status_display(),
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "interview_scheduled_at": self.interview_scheduled_at.isoformat() if self.interview_scheduled_at else None,
            "decision_at": self.decision_at.isoformat() if self.decision_at else None,
            "can_be_withdrawn": self.can_be_withdrawn(),
            "ranking_position": self.ranking_position,
        }
        
        if include_student and self.student:
            data["student"] = self.student.to_dict()
        
        if include_project and self.project:
            data["project"] = self.project.to_dict()
        
        return data
    
    def get_status_display(self) -> str:
        """Get display name for status"""
        status_display = {
            ApplicationStatus.PENDING.value: "Chờ xét duyệt",
            ApplicationStatus.REVIEWING.value: "Đang xem xét",
            ApplicationStatus.SHORTLISTED.value: "Lọt vào vòng trong",
            ApplicationStatus.ACCEPTED.value: "Được chấp nhận",
            ApplicationStatus.REJECTED.value: "Bị từ chối",
            ApplicationStatus.WITHDRAWN.value: "Đã rút"
        }
        return status_display.get(self.status, self.status)
    
    def can_be_withdrawn(self) -> bool:
        """Check if application can be withdrawn"""
        return self.status in [
            ApplicationStatus.PENDING.value,
            ApplicationStatus.REVIEWING.value,
            ApplicationStatus.SHORTLISTED.value
        ]
    
    def accept(self, reviewed_by: uuid.UUID = None):
        """Accept the application"""
        self.status = ApplicationStatus.ACCEPTED.value
        self.decision_at = func.now()
        if reviewed_by:
            self.reviewed_by = reviewed_by
    
    def reject(self, reason: str = None, reviewed_by: uuid.UUID = None):
        """Reject the application"""
        self.status = ApplicationStatus.REJECTED.value
        self.decision_at = func.now()
        self.feedback_to_student = reason
        if reviewed_by:
            self.reviewed_by = reviewed_by
    
    def withdraw(self):
        """Withdraw the application"""
        if self.can_be_withdrawn():
            self.status = ApplicationStatus.WITHDRAWN.value
            self.decision_at = func.now()

# ==================== SKILL LIBRARY MODEL ====================
class SkillLibrary(Base, TimestampMixin):
    __tablename__ = "skills_library"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Skill Information
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), index=True)
    description = Column(Text)
    related_skills = Column(ARRAY(String), default=list)
    popularity_score = Column(Integer, default=0)
    
    # AI Vector
    skill_vector = Column(Vector(384))
    
    # Relationships
    student_skills = relationship("StudentSkill", back_populates="skill")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert skill to dictionary for API response"""
        return {
            "id": str(self.id),
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "related_skills": self.related_skills,
            "popularity_score": self.popularity_score,
        }

# ==================== STUDENT SKILL MODEL ====================
class StudentSkill(Base, TimestampMixin):
    __tablename__ = "student_skills"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relations
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills_library.id"), nullable=False, index=True)
    
    # Verification Levels (1: Lecturer verified, 2: Evidence uploaded, 3: Self-declared)
    verification_level = Column(Integer, nullable=False)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    verification_method = Column(String(50))
    
    # Skill Assessment
    skill_level = Column(String(20))
    confidence_score = Column(Float, default=1.0)
    
    # Evidence
    evidence_urls = Column(ARRAY(String), default=list)
    evidence_description = Column(Text)
    verification_criteria = Column(JSONB, default=list)
    
    # Assessment
    assessment_date = Column(Date, nullable=False)
    expires_at = Column(Date)
    is_renewable = Column(Boolean, default=False)
    
    # Status
    is_verified = Column(Boolean, default=False)
    verification_status = Column(String(20), default="active")
    
    # Relationships
    student = relationship("User", back_populates="verified_skills", foreign_keys=[student_id])
    skill = relationship("SkillLibrary", back_populates="student_skills")
    verifier = relationship("User", back_populates="skill_verifications", foreign_keys=[verified_by])
    project = relationship("Project", foreign_keys=[project_id])
    
    # Constraints
    __table_args__ = (
        CheckConstraint('verification_level IN (1, 2, 3)', name='valid_verification_level'),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='valid_confidence_score'),
    )
    
    @validates('verification_level')
    def validate_verification_level(self, key, level):
        if level not in [1, 2, 3]:
            raise ValueError('Verification level must be 1, 2, or 3')
        return level
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert student skill to dictionary for API response"""
        return {
            "id": str(self.id),
            "skill": self.skill.to_dict() if self.skill else None,
            "verification_level": self.verification_level,
            "verification_method": self.verification_method,
            "skill_level": self.skill_level,
            "skill_level_display": self.get_skill_level_display(),
            "confidence_score": self.confidence_score,
            "evidence_urls": self.evidence_urls,
            "evidence_description": self.evidence_description,
            "assessment_date": self.assessment_date.isoformat() if self.assessment_date else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_verified": self.is_verified,
            "verification_status": self.verification_status,
            "weight": self.get_verification_weight(),
            "is_valid": self.is_valid(),
            "verified_by": str(self.verified_by) if self.verified_by else None,
            "project_id": str(self.project_id) if self.project_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def get_skill_level_display(self) -> str:
        """Get display name for skill level"""
        level_display = {
            SkillLevel.BEGINNER.value: "Mới bắt đầu",
            SkillLevel.INTERMEDIATE.value: "Trung cấp",
            SkillLevel.ADVANCED.value: "Nâng cao",
            SkillLevel.EXPERT.value: "Chuyên gia"
        }
        return level_display.get(self.skill_level, self.skill_level)
    
    def get_verification_weight(self) -> float:
        """Get weight based on verification level"""
        weights = {1: 1.0, 2: 0.7, 3: 0.4}
        return weights.get(self.verification_level, 0.0)
    
    def get_verification_method_display(self) -> str:
        """Get display name for verification method"""
        method_display = {
            VerificationMethod.PROJECT_COMPLETION.value: "Hoàn thành dự án",
            VerificationMethod.EXAM.value: "Bài kiểm tra",
            VerificationMethod.CERTIFICATION.value: "Chứng chỉ",
            VerificationMethod.LECTURER_ASSESSMENT.value: "Đánh giá giảng viên",
            VerificationMethod.WORK_EXPERIENCE.value: "Kinh nghiệm làm việc"
        }
        return method_display.get(self.verification_method, self.verification_method)
    
    def is_valid(self) -> bool:
        """Check if skill verification is still valid"""
        if self.verification_status != "active":
            return False
        
        if self.expires_at and self.expires_at < datetime.now().date():
            return False
        
        return True
    
    def verify(self, verifier_id: uuid.UUID, method: str, level: str, confidence: float = 1.0):
        """Verify the skill"""
        self.verified_by = verifier_id
        self.verification_method = method
        self.skill_level = level
        self.confidence_score = confidence
        self.is_verified = True
        self.verification_status = "active"
        self.assessment_date = datetime.now().date()

# ==================== PROJECT COMPLETION MODEL ====================
class ProjectCompletion(Base, TimestampMixin):
    __tablename__ = "project_completions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relations
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    lecturer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Completion Details
    completion_date = Column(Date, nullable=False)
    grade = Column(String(10))
    grade_points = Column(Float)
    final_report_url = Column(String(500))
    presentation_url = Column(String(500))
    code_repository_url = Column(String(500))
    documentation_url = Column(String(500))
    
    # Skills Assessment
    skills_developed = Column(JSONB, default=list)
    skills_improved = Column(JSONB, default=list)
    new_skills_learned = Column(JSONB, default=list)
    skill_growth_metrics = Column(JSONB, default=dict)
    
    # Feedback
    student_feedback = Column(Text)
    lecturer_feedback = Column(Text)
    peer_feedback = Column(JSONB, default=list)
    project_outcomes = Column(Text)
    challenges_faced = Column(Text)
    lessons_learned = Column(Text)
    future_recommendations = Column(Text)
    
    # Ratings
    student_rating = Column(Integer)
    lecturer_rating = Column(Integer)
    project_rating = Column(Integer)
    
    # Recommendations
    would_recommend = Column(Boolean)
    testimonial = Column(Text)
    is_testimonial_public = Column(Boolean, default=False)
    featured = Column(Boolean, default=False)
    
    # Metadata
    completion_certificate_url = Column(String(500))
    completion_verified = Column(Boolean, default=False)
    
    # Relationships
    project = relationship("Project", back_populates="completions")
    student = relationship("User", foreign_keys=[student_id])
    lecturer = relationship("User", foreign_keys=[lecturer_id])
    
    # Constraints
    __table_args__ = (
        CheckConstraint('student_rating IS NULL OR (student_rating >= 1 AND student_rating <= 5)', name='valid_student_rating'),
        CheckConstraint('lecturer_rating IS NULL OR (lecturer_rating >= 1 AND lecturer_rating <= 5)', name='valid_lecturer_rating'),
        CheckConstraint('project_rating IS NULL OR (project_rating >= 1 AND project_rating <= 5)', name='valid_project_rating'),
    )
    
    def to_dict(self, include_student: bool = True, include_project: bool = True) -> Dict[str, Any]:
        """Convert project completion to dictionary for API response"""
        data = {
            "id": str(self.id),
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
            "grade": self.grade,
            "grade_points": self.grade_points,
            "grade_display": self.get_grade_display(),
            "final_report_url": self.final_report_url,
            "presentation_url": self.presentation_url,
            "code_repository_url": self.code_repository_url,
            "student_feedback": self.student_feedback,
            "lecturer_feedback": self.lecturer_feedback,
            "student_rating": self.student_rating,
            "lecturer_rating": self.lecturer_rating,
            "project_rating": self.project_rating,
            "would_recommend": self.would_recommend,
            "testimonial": self.testimonial,
            "is_testimonial_public": self.is_testimonial_public,
            "featured": self.featured,
            "completion_certificate_url": self.completion_certificate_url,
            "completion_verified": self.completion_verified,
            "skills_developed": self.skills_developed,
            "skills_improved": self.skills_improved,
            "new_skills_learned": self.new_skills_learned,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_student and self.student:
            data["student"] = self.student.to_dict()
        
        if include_project and self.project:
            data["project"] = self.project.to_dict()
        
        if self.lecturer:
            data["lecturer"] = self.lecturer.to_dict()
        
        return data
    
    def get_grade_display(self) -> str:
        """Get display name for grade"""
        grade_display = {
            "A": "Xuất sắc",
            "B": "Tốt",
            "C": "Khá",
            "D": "Trung bình",
            "F": "Không đạt"
        }
        return grade_display.get(self.grade, self.grade)
    
    def verify_skills(self):
        """Automatically verify skills based on completion"""
        if self.skills_developed and self.lecturer_id:
            # This would trigger creation of StudentSkill records with verification_level = 1
            pass

# ==================== NOTIFICATION MODEL ====================
class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Recipient
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Notification Details
    type = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSONB, default=dict)
    
    # Status
    is_read = Column(Boolean, default=False, index=True)
    is_archived = Column(Boolean, default=False)
    priority = Column(String(20), default="normal")
    delivery_method = Column(String(20), default="in_app")
    
    # Actions
    action_url = Column(String(500))
    action_label = Column(String(100))
    action_data = Column(JSONB, default=dict)
    
    # Timestamps
    scheduled_for = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary for API response"""
        return {
            "id": str(self.id),
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "is_read": self.is_read,
            "priority": self.priority,
            "action_url": self.action_url,
            "action_label": self.action_label,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "type_display": self.get_type_display(),
        }
    
    def get_type_display(self) -> str:
        """Get display name for notification type"""
        type_display = {
            "application_submitted": "Nộp đơn thành công",
            "application_updated": "Cập nhật đơn xin",
            "application_accepted": "Đơn xin được chấp nhận",
            "application_rejected": "Đơn xin bị từ chối",
            "project_match": "Đề tài phù hợp mới",
            "deadline_reminder": "Nhắc nhở hạn chót",
            "message_received": "Tin nhắn mới",
            "skill_verified": "Kỹ năng được xác thực",
            "project_published": "Đề tài mới được đăng",
            "system_announcement": "Thông báo hệ thống",
            "weekly_digest": "Tóm tắt hàng tuần"
        }
        return type_display.get(self.type, self.type)
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = func.now()
    
    def is_expired(self) -> bool:
        """Check if notification is expired"""
        if self.expires_at and self.expires_at < func.now():
            return True
        return False

# ==================== MESSAGE MODEL ====================
class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Thread Management
    conversation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"))
    
    # Participants
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), index=True)
    
    # Content
    message_type = Column(String(20), default="text")
    content = Column(Text, nullable=False)
    attachments = Column(JSONB, default=list)
    
    # Status
    is_read = Column(Boolean, default=False)
    is_delivered = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    
    # Metadata
    message_metadata = Column(JSONB, default=dict)
    
    # Timestamps
    read_at = Column(DateTime(timezone=True))
    
    # Relationships
    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    recipient = relationship("User", back_populates="received_messages", foreign_keys=[recipient_id])
    project = relationship("Project", back_populates="messages")
    parent = relationship("Message", remote_side=[id], backref="replies")
    
    def to_dict(self, include_sender: bool = True, include_recipient: bool = False) -> Dict[str, Any]:
        """Convert message to dictionary for API response"""
        data = {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "content": self.content,
            "message_type": self.message_type,
            "attachments": self.attachments,
            "is_read": self.is_read,
            "is_delivered": self.is_delivered,
            "is_edited": self.is_edited,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }
        
        if include_sender and self.sender:
            data["sender"] = self.sender.to_dict()
        
        if include_recipient and self.recipient:
            data["recipient"] = self.recipient.to_dict()
        
        if self.project:
            data["project"] = self.project.to_dict()
        
        if self.parent_message_id:
            data["parent_message_id"] = str(self.parent_message_id)
        
        return data
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = func.now()
    
    def mark_as_delivered(self):
        """Mark message as delivered"""
        if not self.is_delivered:
            self.is_delivered = True

# ==================== SYSTEM CONFIG MODEL ====================
class SystemConfig(Base, TimestampMixin):
    __tablename__ = "system_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(JSONB, nullable=False)
    config_type = Column(String(50), default="string")
    description = Column(Text)
    is_public = Column(Boolean, default=False)
    is_editable = Column(Boolean, default=True)
    
    # Versioning
    version = Column(Integer, default=1)
    previous_value = Column(JSONB)
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Timestamps
    effective_from = Column(DateTime(timezone=True), default=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert system config to dictionary for API response"""
        return {
            "id": str(self.id),
            "config_key": self.config_key,
            "config_value": self.config_value,
            "config_type": self.config_type,
            "description": self.description,
            "is_public": self.is_public,
            "is_editable": self.is_editable,
            "version": self.version,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def is_active(self) -> bool:
        """Check if config is active"""
        now = func.now()
        if self.effective_from and self.effective_from > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True

# ==================== AUDIT LOG MODEL ====================
class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Actor
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    user_role = Column(String(20))
    
    # Action
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), index=True)
    entity_id = Column(UUID(as_uuid=True))
    entity_name = Column(String(200))
    
    # Changes
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    changed_fields = Column(ARRAY(String), default=list)
    
    # Context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    request_url = Column(String(500))
    request_method = Column(String(10))
    
    # Severity
    severity = Column(String(20), default="info")
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary for API response"""
        return {
            "id": str(self.id),
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id) if self.entity_id else None,
            "entity_name": self.entity_name,
            "user_id": str(self.user_id) if self.user_id else None,
            "user_role": self.user_role,
            "changed_fields": self.changed_fields,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "severity": self.severity,
            "ip_address": self.ip_address,
            "request_url": self.request_url,
            "request_method": self.request_method,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

# ==================== ANALYTICS MODEL ====================
class Analytics(Base, TimestampMixin):
    __tablename__ = "analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event Information
    event_type = Column(String(100), nullable=False, index=True)
    event_name = Column(String(200), nullable=False)
    page_url = Column(String(500))
    referrer_url = Column(String(500))
    
    # User Context
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    user_role = Column(String(20))
    session_id = Column(String(100), index=True)
    
    # Device & Browser
    user_agent = Column(Text)
    ip_address = Column(String(45))
    device_type = Column(String(50))
    browser_name = Column(String(50))
    os_name = Column(String(50))
    screen_resolution = Column(String(20))
    
    # Event Data
    event_data = Column(JSONB, default=dict)
    event_value = Column(Float)
    event_duration = Column(Integer)
    
    # Geolocation
    country = Column(String(100))
    city = Column(String(100))
    region = Column(String(100))
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analytics to dictionary for API response"""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "event_name": self.event_name,
            "user_id": str(self.user_id) if self.user_id else None,
            "user_role": self.user_role,
            "session_id": self.session_id,
            "page_url": self.page_url,
            "referrer_url": self.referrer_url,
            "device_type": self.device_type,
            "browser_name": self.browser_name,
            "country": self.country,
            "city": self.city,
            "event_data": self.event_data,
            "event_value": self.event_value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

# ==================== DATABASE INITIALIZATION ====================
def init_db(engine):
    """Initialize database with all models"""
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database initialized with tables:")
    for table in Base.metadata.tables:
        print(f"   - {table}")
    
    print(f"\n📊 Total tables: {len(Base.metadata.tables)}")