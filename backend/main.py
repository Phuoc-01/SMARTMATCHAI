"""
SMART-MATCH AI - FastAPI Backend Application
Production-ready với đầy đủ API endpoints
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, status, Query, Path, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from pydantic import BaseModel, Field, EmailStr, validator
from sqlalchemy.orm import Session
import logging
from contextlib import asynccontextmanager

from .config.database import SessionLocal, engine, Base
from .models import (
    User, Project, Application, StudentSkill, SkillLibrary, 
    ProjectCompletion, Notification, Message, SystemConfig,
    UserRole, ProjectStatus, ApplicationStatus, SkillLevel
)
from .services.ai_matching import SmartMatchAIService, create_ai_matching_service
from .services.auth import (
    create_access_token, create_refresh_token, verify_token,
    hash_password, verify_password, get_current_user
)
from .services.email import EmailService
from .services.file_upload import FileUploadService
from .middleware.auth import AuthMiddleware
from .middleware.logging import LoggingMiddleware
from .utils.validators import validate_email_dut, validate_phone, validate_student_id
from .utils.helpers import generate_slug, calculate_age

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== LIFESPAN MANAGEMENT ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting SMART-MATCH AI Backend...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created")
    
    # Initialize AI service
    app.state.ai_service = create_ai_matching_service()
    logger.info("✅ AI Matching Service initialized")
    
    # Initialize other services
    app.state.email_service = EmailService()
    app.state.file_upload_service = FileUploadService()
    logger.info("✅ Services initialized")
    
    yield
    
    logger.info("🛑 Shutting down SMART-MATCH AI Backend...")

# ==================== FASTAPI APP ====================
app = FastAPI(
    title="SMART-MATCH AI API",
    description="Nền tảng matching đề tài NCKH & năng lực sinh viên Đại học Bách Khoa Đà Nẵng",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# ==================== MIDDLEWARE ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)

# ==================== DEPENDENCIES ====================
security = HTTPBearer()

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_ai_service():
    """AI service dependency"""
    return app.state.ai_service

def get_email_service():
    """Email service dependency"""
    return app.state.email_service

def get_file_upload_service():
    """File upload service dependency"""
    return app.state.file_upload_service

# ==================== PYDANTIC MODELS ====================
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    
    @validator('email')
    def validate_email_domain(cls, v):
        if not v.endswith('@dut.edu.vn'):
            raise ValueError('Email must be a DUT email address')
        return v

class StudentCreate(UserBase):
    password: str = Field(..., min_length=8)
    student_id: str
    class_code: str
    faculty: str
    major: str
    year_of_study: int = Field(..., ge=1, le=5)
    
    @validator('student_id')
    def validate_student_id(cls, v):
        if not v.isdigit() or len(v) != 9:
            raise ValueError('Student ID must be 9 digits')
        return v

class LecturerCreate(UserBase):
    password: str = Field(..., min_length=8)
    lecturer_code: str
    department: str
    academic_title: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    faculty: Optional[str] = None
    avatar_url: Optional[str] = None
    is_verified: bool
    profile_completion_percentage: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class StudentResponse(UserResponse):
    student_id: str
    class_code: str
    major: str
    year_of_study: int
    gpa: Optional[float] = None
    technical_skills: List[str] = []
    soft_skills: List[str] = []
    total_projects_completed: int = 0
    avg_project_rating: float = 0.0

class LecturerResponse(UserResponse):
    lecturer_code: str
    department: str
    academic_title: str
    office_location: Optional[str] = None
    research_interests: List[str] = []

class ProjectBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=50)
    short_description: Optional[str] = Field(None, max_length=500)
    research_field: str
    project_type: str
    difficulty_level: str = "intermediate"
    
    # Requirements
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    prerequisites: Optional[str] = None
    learning_outcomes: List[str] = []
    
    # Logistics
    duration_weeks: int = Field(..., ge=1, le=52)
    time_commitment_hours: int = Field(..., ge=5, le=40)
    max_students: int = Field(1, ge=1, le=10)
    min_students: int = Field(1, ge=1, le=10)
    is_paid: bool = False
    stipend_amount: Optional[float] = None
    funding_source: Optional[str] = None
    
    # Timeline
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    application_deadline: datetime
    
    # Metadata
    tags: List[str] = []
    keywords: List[str] = []
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        if 'start_date' in values and values['start_date'] and v:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
        return v

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    application_deadline: Optional[datetime] = None

class ProjectResponse(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    description: str
    short_description: Optional[str] = None
    research_field: str
    project_type: str
    difficulty_level: str
    required_skills: List[str]
    preferred_skills: List[str]
    duration_weeks: int
    time_commitment_hours: int
    max_students: int
    is_paid: bool
    stipend_amount: Optional[float] = None
    application_deadline: datetime
    status: str
    faculty: str
    view_count: int
    application_count: int
    avg_match_score: float
    lecturer: LecturerResponse
    created_at: datetime
    days_until_deadline: Optional[int] = None
    is_accepting_applications: bool
    
    class Config:
        from_attributes = True

class ApplicationCreate(BaseModel):
    cover_letter: str = Field(..., min_length=50, max_length=2000)
    relevant_experience: Optional[str] = None
    motivation: Optional[str] = None

class ApplicationResponse(BaseModel):
    id: uuid.UUID
    match_score: float
    cover_letter: str
    status: str
    status_display: str
    applied_at: datetime
    reviewed_at: Optional[datetime] = None
    student: StudentResponse
    project: ProjectResponse
    
    class Config:
        from_attributes = True

class MatchResult(BaseModel):
    match_score: float
    match_level: str
    breakdown: Dict[str, float]
    skill_match_details: Dict[str, Any]
    recommendation: str
    missing_skills: List[str]

class SkillVerificationCreate(BaseModel):
    skill_name: str
    verification_level: int = Field(..., ge=1, le=3)
    evidence_urls: Optional[List[str]] = None
    evidence_description: Optional[str] = None
    skill_level: Optional[str] = "intermediate"

class SkillVerificationResponse(BaseModel):
    id: uuid.UUID
    skill_name: str
    verification_level: int
    verification_method: Optional[str] = None
    skill_level: Optional[str] = None
    confidence_score: float
    evidence_urls: List[str]
    is_verified: bool
    verification_status: str
    assessment_date: datetime
    expires_at: Optional[datetime] = None
    weight: float
    is_valid: bool
    
    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    message: str
    is_read: bool
    priority: str
    action_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==================== HEALTH CHECK ====================
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "service": "SMART-MATCH AI API",
        "version": "2.0.0",
        "status": "operational",
        "description": "Nền tảng matching đề tài NCKH & năng lực sinh viên",
        "university": "Đại học Bách Khoa - Đại học Đà Nẵng",
        "contact": "smartmatch@dut.edu.vn"
    }

@app.get("/health", tags=["Health"])
async def health_check(
    db: Session = Depends(get_db),
    ai_service: SmartMatchAIService = Depends(get_ai_service)
):
    """Health check endpoint"""
    try:
        # Check database
        db.execute("SELECT 1")
        
        # Check AI service
        ai_stats = ai_service.get_system_stats()
        
        return {
            "status": "healthy",
            "database": "connected",
            "ai_service": "operational",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unavailable: {str(e)}"
        )

# ==================== AUTH ENDPOINTS ====================
@app.post("/api/auth/register/student", response_model=UserResponse, tags=["Authentication"])
async def register_student(
    student_data: StudentCreate,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """Register a new student"""
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == student_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if student ID already exists
        existing_student = db.query(User).filter(
            User.student_id == student_data.student_id
        ).first()
        if existing_student:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student ID already registered"
            )
        
        # Create new user
        user = User(
            email=student_data.email,
            full_name=student_data.full_name,
            role=UserRole.STUDENT.value,
            student_id=student_data.student_id,
            class_code=student_data.class_code,
            faculty=student_data.faculty,
            major=student_data.major,
            year_of_study=student_data.year_of_study,
            is_verified=False
        )
        
        # Hash password
        user.set_password(student_data.password)
        
        # Generate verification token
        user.verification_token = str(uuid.uuid4())
        
        # Save to database
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Calculate profile completion
        user.profile_completion_percentage = user.calculate_profile_completion()
        db.commit()
        
        # Send verification email (in background)
        if background_tasks:
            email_service = EmailService()
            background_tasks.add_task(
                email_service.send_verification_email,
                user.email,
                user.full_name,
                user.verification_token
            )
        
        logger.info(f"New student registered: {user.email} ({user.student_id})")
        
        return user
        
    except Exception as e:
        db.rollback()
        logger.error(f"Student registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@app.post("/api/auth/register/lecturer", response_model=UserResponse, tags=["Authentication"])
async def register_lecturer(
    lecturer_data: LecturerCreate,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """Register a new lecturer"""
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == lecturer_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if lecturer code already exists
        existing_lecturer = db.query(User).filter(
            User.lecturer_code == lecturer_data.lecturer_code
        ).first()
        if existing_lecturer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lecturer code already registered"
            )
        
        # Create new user
        user = User(
            email=lecturer_data.email,
            full_name=lecturer_data.full_name,
            role=UserRole.LECTURER.value,
            lecturer_code=lecturer_data.lecturer_code,
            department=lecturer_data.department,
            academic_title=lecturer_data.academic_title,
            is_verified=False
        )
        
        # Hash password
        user.set_password(lecturer_data.password)
        
        # Generate verification token
        user.verification_token = str(uuid.uuid4())
        
        # Save to database
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Calculate profile completion
        user.profile_completion_percentage = user.calculate_profile_completion()
        db.commit()
        
        # Send verification email (in background)
        if background_tasks:
            email_service = EmailService()
            background_tasks.add_task(
                email_service.send_verification_email,
                user.email,
                user.full_name,
                user.verification_token
            )
        
        logger.info(f"New lecturer registered: {user.email} ({user.lecturer_code})")
        
        return user
        
    except Exception as e:
        db.rollback()
        logger.error(f"Lecturer registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@app.post("/api/auth/login", tags=["Authentication"])
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Login user"""
    try:
        # Find user
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check password
        if not user.check_password(login_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Update last login
        user.last_login_at = datetime.now()
        db.commit()
        
        # Create tokens
        access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Get user data
        user_data = user.to_dict()
        
        logger.info(f"User logged in: {user.email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,  # 1 hour
            "user": user_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@app.post("/api/auth/refresh", tags=["Authentication"])
async def refresh_token(
    refresh_token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    try:
        # Verify refresh token
        payload = verify_token(refresh_token, is_refresh=True)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new access token
        access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 3600
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@app.get("/api/auth/verify/{token}", tags=["Authentication"])
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify user email"""
    try:
        user = db.query(User).filter(User.verification_token == token).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid verification token"
            )
        
        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        # Verify email
        user.email_verified = True
        user.is_verified = True
        user.verification_token = None
        db.commit()
        
        logger.info(f"Email verified: {user.email}")
        
        return {
            "message": "Email verified successfully",
            "user": user.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )

@app.post("/api/auth/forgot-password", tags=["Authentication"])
async def forgot_password(
    email: EmailStr,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """Request password reset"""
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Don't reveal that user doesn't exist
            return {"message": "If the email exists, a reset link will be sent"}
        
        # Generate reset token
        user.reset_token = str(uuid.uuid4())
        user.reset_token_expires = datetime.now() + timedelta(hours=24)
        db.commit()
        
        # Send reset email (in background)
        if background_tasks:
            email_service = EmailService()
            background_tasks.add_task(
                email_service.send_password_reset_email,
                user.email,
                user.full_name,
                user.reset_token
            )
        
        logger.info(f"Password reset requested: {user.email}")
        
        return {"message": "Password reset email sent"}
        
    except Exception as e:
        logger.error(f"Password reset request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )

@app.post("/api/auth/reset-password", tags=["Authentication"])
async def reset_password(
    token: str = Query(...),
    new_password: str = Query(..., min_length=8),
    db: Session = Depends(get_db)
):
    """Reset password with token"""
    try:
        user = db.query(User).filter(
            User.reset_token == token,
            User.reset_token_expires > datetime.now()
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Update password
        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()
        
        logger.info(f"Password reset: {user.email}")
        
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )

# ==================== USER PROFILE ENDPOINTS ====================
@app.get("/api/users/me", response_model=UserResponse, tags=["Users"])
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile"""
    return current_user

@app.put("/api/users/me", response_model=UserResponse, tags=["Users"])
async def update_user_profile(
    update_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    try:
        # Update allowed fields
        allowed_fields = [
            'full_name', 'bio', 'phone', 'linkedin_url', 
            'github_url', 'portfolio_url', 'avatar_url'
        ]
        
        if current_user.role == UserRole.STUDENT.value:
            allowed_fields.extend([
                'class_code', 'major', 'gpa', 'year_of_study',
                'technical_skills', 'soft_skills'
            ])
        elif current_user.role == UserRole.LECTURER.value:
            allowed_fields.extend([
                'academic_title', 'office_location', 'office_hours',
                'research_interests', 'publications'
            ])
        
        # Update fields
        for field, value in update_data.items():
            if field in allowed_fields and hasattr(current_user, field):
                setattr(current_user, field, value)
        
        # Update profile completion
        current_user.profile_completion_percentage = current_user.calculate_profile_completion()
        
        # Update timestamps
        current_user.updated_at = datetime.now()
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"User profile updated: {current_user.email}")
        
        return current_user
        
    except Exception as e:
        db.rollback()
        logger.error(f"Profile update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}"
        )

@app.get("/api/users/students", response_model=List[StudentResponse], tags=["Users"])
async def get_students(
    faculty: Optional[str] = None,
    major: Optional[str] = None,
    year_of_study: Optional[int] = None,
    has_verified_skills: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get students with filtering"""
    try:
        query = db.query(User).filter(User.role == UserRole.STUDENT.value)
        
        # Apply filters
        if faculty:
            query = query.filter(User.faculty == faculty)
        if major:
            query = query.filter(User.major == major)
        if year_of_study:
            query = query.filter(User.year_of_study == year_of_study)
        if has_verified_skills is not None:
            # This would require a join with student_skills table
            pass
        
        # Pagination
        total = query.count()
        students = query.offset((page - 1) * limit).limit(limit).all()
        
        return {
            "data": students,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get students: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get students"
        )

@app.get("/api/users/lecturers", response_model=List[LecturerResponse], tags=["Users"])
async def get_lecturers(
    department: Optional[str] = None,
    faculty: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get lecturers with filtering"""
    try:
        query = db.query(User).filter(User.role == UserRole.LECTURER.value)
        
        # Apply filters
        if department:
            query = query.filter(User.department == department)
        if faculty:
            query = query.filter(User.faculty == faculty)
        
        # Pagination
        total = query.count()
        lecturers = query.offset((page - 1) * limit).limit(limit).all()
        
        return {
            "data": lecturers,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get lecturers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get lecturers"
        )

@app.get("/api/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def get_user_by_id(
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get user by ID"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        )

# ==================== PROJECT ENDPOINTS ====================
@app.get("/api/projects", response_model=List[ProjectResponse], tags=["Projects"])
async def get_projects(
    status: Optional[str] = None,
    faculty: Optional[str] = None,
    research_field: Optional[str] = None,
    difficulty_level: Optional[str] = None,
    is_paid: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get projects with filtering and search"""
    try:
        query = db.query(Project)
        
        # Apply filters
        if status:
            query = query.filter(Project.status == status)
        if faculty:
            query = query.filter(Project.faculty == faculty)
        if research_field:
            query = query.filter(Project.research_field == research_field)
        if difficulty_level:
            query = query.filter(Project.difficulty_level == difficulty_level)
        if is_paid is not None:
            query = query.filter(Project.is_paid == is_paid)
        
        # Apply search
        if search:
            query = query.filter(
                (Project.title.ilike(f"%{search}%")) |
                (Project.description.ilike(f"%{search}%")) |
                (Project.research_field.ilike(f"%{search}%"))
            )
        
        # Only show published projects to non-authenticated users
        # (This would be handled by middleware)
        
        # Order by creation date (newest first)
        query = query.order_by(Project.created_at.desc())
        
        # Pagination
        total = query.count()
        projects = query.offset((page - 1) * limit).limit(limit).all()
        
        return {
            "data": projects,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get projects"
        )

@app.get("/api/projects/featured", response_model=List[ProjectResponse], tags=["Projects"])
async def get_featured_projects(
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get featured projects"""
    try:
        projects = db.query(Project).filter(
            Project.is_featured == True,
            Project.status == ProjectStatus.PUBLISHED.value
        ).order_by(
            Project.priority.desc(),
            Project.created_at.desc()
        ).limit(limit).all()
        
        return projects
        
    except Exception as e:
        logger.error(f"Failed to get featured projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get featured projects"
        )

@app.post("/api/projects", response_model=ProjectResponse, tags=["Projects"])
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_service: SmartMatchAIService = Depends(get_ai_service)
):
    """Create a new project (lecturer only)"""
    if current_user.role != UserRole.LECTURER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lecturers can create projects"
        )
    
    try:
        # Generate slug from title
        slug = generate_slug(project_data.title)
        
        # Check if slug already exists
        existing_project = db.query(Project).filter(Project.slug == slug).first()
        if existing_project:
            # Add timestamp to make slug unique
            slug = f"{slug}-{int(datetime.now().timestamp())}"
        
        # Create project
        project = Project(
            slug=slug,
            title=project_data.title,
            description=project_data.description,
            short_description=project_data.short_description,
            research_field=project_data.research_field,
            project_type=project_data.project_type,
            difficulty_level=project_data.difficulty_level,
            required_skills=project_data.required_skills,
            preferred_skills=project_data.preferred_skills,
            prerequisites=project_data.prerequisites,
            learning_outcomes=project_data.learning_outcomes,
            duration_weeks=project_data.duration_weeks,
            time_commitment_hours=project_data.time_commitment_hours,
            max_students=project_data.max_students,
            min_students=project_data.min_students,
            is_paid=project_data.is_paid,
            stipend_amount=project_data.stipend_amount,
            funding_source=project_data.funding_source,
            start_date=project_data.start_date,
            end_date=project_data.end_date,
            application_deadline=project_data.application_deadline,
            tags=project_data.tags,
            keywords=project_data.keywords,
            lecturer_id=current_user.id,
            faculty=current_user.faculty,
            status=ProjectStatus.DRAFT.value
        )
        
        # Generate AI vector for project
        project.requirement_vector = ai_service.create_project_vector(project)
        
        db.add(project)
        db.commit()
        db.refresh(project)
        
        logger.info(f"Project created: {project.title} by {current_user.email}")
        
        return project
        
    except Exception as e:
        db.rollback()
        logger.error(f"Project creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project creation failed: {str(e)}"
        )

@app.get("/api/projects/{project_id_or_slug}", response_model=ProjectResponse, tags=["Projects"])
async def get_project(
    project_id_or_slug: str,
    db: Session = Depends(get_db)
):
    """Get project by ID or slug"""
    try:
        # Try to parse as UUID
        try:
            project_id = uuid.UUID(project_id_or_slug)
            project = db.query(Project).filter(Project.id == project_id).first()
        except ValueError:
            # Treat as slug
            project = db.query(Project).filter(Project.slug == project_id_or_slug).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Increment view count
        project.increment_view_count()
        db.commit()
        
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project"
        )

@app.put("/api/projects/{project_id}", response_model=ProjectResponse, tags=["Projects"])
async def update_project(
    project_id: uuid.UUID,
    update_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update project (lecturer only)"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check ownership
        if project.lecturer_id != current_user.id and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this project"
            )
        
        # Update fields
        for field, value in update_data.dict(exclude_unset=True).items():
            if hasattr(project, field):
                setattr(project, field, value)
        
        project.updated_at = datetime.now()
        db.commit()
        db.refresh(project)
        
        logger.info(f"Project updated: {project.title} by {current_user.email}")
        
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Project update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project update failed: {str(e)}"
        )

@app.post("/api/projects/{project_id}/publish", response_model=ProjectResponse, tags=["Projects"])
async def publish_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Publish project (make it visible to students)"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check ownership
        if project.lecturer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to publish this project"
            )
        
        # Check if project can be published
        if project.status != ProjectStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project is already {project.status}"
            )
        
        # Publish project
        project.status = ProjectStatus.PUBLISHED.value
        project.published_at = datetime.now()
        db.commit()
        
        logger.info(f"Project published: {project.title} by {current_user.email}")
        
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Project publish failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project publish failed: {str(e)}"
        )

# ==================== AI MATCHING ENDPOINTS ====================
@app.get("/api/matching/student/recommended", tags=["AI Matching"])
async def get_recommended_projects_for_student(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_service: SmartMatchAIService = Depends(get_ai_service),
    limit: int = Query(10, ge=1, le=50)
):
    """Get recommended projects for current student"""
    if current_user.role != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can get project recommendations"
        )
    
    try:
        # Get available projects
        projects = db.query(Project).filter(
            Project.status == ProjectStatus.PUBLISHED.value,
            Project.application_deadline > datetime.now()
        ).all()
        
        # Get recommendations
        recommendations = ai_service.find_recommended_projects(
            student=current_user,
            projects=projects,
            limit=limit
        )
        
        return {
            "student": current_user.to_dict(),
            "recommendations": recommendations,
            "total_projects": len(projects)
        }
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recommendations"
        )

@app.get("/api/matching/project/{project_id}/applicants/ranked", tags=["AI Matching"])
async def get_ranked_applicants_for_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_service: SmartMatchAIService = Depends(get_ai_service)
):
    """Get ranked applicants for a project (lecturer only)"""
    if current_user.role != UserRole.LECTURER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lecturers can view ranked applicants"
        )
    
    try:
        # Get project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check ownership
        if project.lecturer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view applicants for this project"
            )
        
        # Get applicants
        applicants = db.query(User).join(Application).filter(
            Application.project_id == project_id,
            Application.status.in_([
                ApplicationStatus.PENDING.value,
                ApplicationStatus.REVIEWING.value,
                ApplicationStatus.SHORTLISTED.value
            ])
        ).all()
        
        # Rank applicants using AI
        ranked_applicants = ai_service.rank_applicants(project, applicants)
        
        return {
            "project": project.to_dict(),
            "ranked_applicants": ranked_applicants,
            "total_applicants": len(applicants)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rank applicants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rank applicants"
        )

@app.get("/api/matching/calculate/{project_id}", response_model=MatchResult, tags=["AI Matching"])
async def calculate_match_score(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_service: SmartMatchAIService = Depends(get_ai_service)
):
    """Calculate match score between current student and project"""
    if current_user.role != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can calculate match scores"
        )
    
    try:
        # Get project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Calculate match score
        match_result = ai_service.calculate_comprehensive_match_score(
            student=current_user,
            project=project
        )
        
        return match_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate match score: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate match score"
        )

# ==================== APPLICATION ENDPOINTS ====================
@app.get("/api/applications/student/my-applications", tags=["Applications"])
async def get_my_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get current student's applications"""
    if current_user.role != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can view their applications"
        )
    
    try:
        query = db.query(Application).filter(
            Application.student_id == current_user.id
        )
        
        if status:
            query = query.filter(Application.status == status)
        
        # Order by application date (newest first)
        query = query.order_by(Application.applied_at.desc())
        
        # Pagination
        total = query.count()
        applications = query.offset((page - 1) * limit).limit(limit).all()
        
        return {
            "data": [app.to_dict(include_project=True) for app in applications],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get applications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get applications"
        )

@app.post("/api/applications/apply/{project_id}", response_model=ApplicationResponse, tags=["Applications"])
async def apply_to_project(
    project_id: uuid.UUID,
    application_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_service: SmartMatchAIService = Depends(get_ai_service)
):
    """Apply to a project (student only)"""
    if current_user.role != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can apply to projects"
        )
    
    try:
        # Get project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if project is accepting applications
        if not project.is_accepting_applications():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project is not accepting applications"
            )
        
        # Check if student has already applied
        existing_application = db.query(Application).filter(
            Application.project_id == project_id,
            Application.student_id == current_user.id
        ).first()
        
        if existing_application:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already applied to this project"
            )
        
        # Calculate match score using AI
        match_result = ai_service.calculate_comprehensive_match_score(
            student=current_user,
            project=project
        )
        
        # Create application
        application = Application(
            project_id=project_id,
            student_id=current_user.id,
            match_score=match_result["match_score"],
            match_details=match_result,
            match_breakdown=match_result["breakdown"],
            cover_letter=application_data.cover_letter,
            relevant_experience=application_data.relevant_experience,
            motivation=application_data.motivation,
            status=ApplicationStatus.PENDING.value
        )
        
        db.add(application)
        
        # Update project application count
        project.increment_application_count()
        
        db.commit()
        db.refresh(application)
        
        logger.info(f"Application submitted: {current_user.email} to {project.title}")
        
        # TODO: Send notification to lecturer
        
        return application
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Application submission failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Application submission failed: {str(e)}"
        )

@app.get("/api/applications/project/{project_id}", tags=["Applications"])
async def get_project_applications(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get applications for a project (lecturer only)"""
    if current_user.role != UserRole.LECTURER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lecturers can view project applications"
        )
    
    try:
        # Get project and check ownership
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if project.lecturer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view applications for this project"
            )
        
        query = db.query(Application).filter(
            Application.project_id == project_id
        )
        
        if status:
            query = query.filter(Application.status == status)
        
        # Order by match score (highest first)
        query = query.order_by(Application.match_score.desc(), Application.applied_at.desc())
        
        # Pagination
        total = query.count()
        applications = query.offset((page - 1) * limit).limit(limit).all()
        
        return {
            "project": project.to_dict(),
            "data": [app.to_dict(include_student=True) for app in applications],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project applications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project applications"
        )

@app.put("/api/applications/{application_id}/status", response_model=ApplicationResponse, tags=["Applications"])
async def update_application_status(
    application_id: uuid.UUID,
    status_update: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update application status (lecturer only)"""
    if current_user.role != UserRole.LECTURER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lecturers can update application status"
        )
    
    try:
        application = db.query(Application).filter(Application.id == application_id).first()
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Get project and check ownership
        project = db.query(Project).filter(Project.id == application.project_id).first()
        if project.lecturer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this application"
            )
        
        new_status = status_update.get("status")
        feedback = status_update.get("feedback")
        
        if not new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status is required"
            )
        
        # Validate status
        valid_statuses = [s.value for s in ApplicationStatus]
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Update application
        application.status = new_status
        application.reviewed_at = datetime.now()
        application.reviewed_by = current_user.id
        
        if feedback:
            application.feedback_to_student = feedback
        
        if new_status == ApplicationStatus.ACCEPTED.value:
            application.decision_at = datetime.now()
        elif new_status == ApplicationStatus.REJECTED.value:
            application.decision_at = datetime.now()
        
        db.commit()
        db.refresh(application)
        
        logger.info(f"Application status updated: {application_id} to {new_status}")
        
        # TODO: Send notification to student
        
        return application
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update application status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update application status: {str(e)}"
        )

@app.delete("/api/applications/{application_id}", tags=["Applications"])
async def withdraw_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Withdraw application (student only)"""
    if current_user.role != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can withdraw applications"
        )
    
    try:
        application = db.query(Application).filter(Application.id == application_id).first()
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Check ownership
        if application.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to withdraw this application"
            )
        
        # Check if can be withdrawn
        if not application.can_be_withdrawn():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot withdraw application in current status"
            )
        
        # Withdraw application
        application.withdraw()
        db.commit()
        
        logger.info(f"Application withdrawn: {application_id} by {current_user.email}")
        
        return {"message": "Application withdrawn successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to withdraw application: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to withdraw application: {str(e)}"
        )

# ==================== SKILL VERIFICATION ENDPOINTS ====================
@app.get("/api/skills/student/my-skills", tags=["Skills"])
async def get_my_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current student's skills with verification"""
    if current_user.role != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can view their skills"
        )
    
    try:
        # Get student skills with verification
        student_skills = db.query(StudentSkill).filter(
            StudentSkill.student_id == current_user.id
        ).all()
        
        # Group by skill
        skills_by_name = {}
        for skill in student_skills:
            skill_name = skill.skill_name
            if skill_name not in skills_by_name:
                skills_by_name[skill_name] = {
                    "skill_name": skill_name,
                    "verifications": [],
                    "highest_verification_level": 0,
                    "is_verified": False
                }
            
            skills_by_name[skill_name]["verifications"].append(skill.to_dict())
            
            # Track highest verification level
            if skill.verification_level > skills_by_name[skill_name]["highest_verification_level"]:
                skills_by_name[skill_name]["highest_verification_level"] = skill.verification_level
                skills_by_name[skill_name]["is_verified"] = skill.is_verified
        
        return {
            "skills": list(skills_by_name.values()),
            "total_skills": len(skills_by_name),
            "verified_skills_count": sum(1 for s in skills_by_name.values() if s["is_verified"])
        }
        
    except Exception as e:
        logger.error(f"Failed to get student skills: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get student skills"
        )

@app.post("/api/skills/student/add-skill", response_model=SkillVerificationResponse, tags=["Skills"])
async def add_student_skill(
    skill_data: SkillVerificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new skill for student (self-declared)"""
    if current_user.role != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can add skills"
        )
    
    try:
        # Create student skill with self-declared verification (level 3)
        student_skill = StudentSkill(
            student_id=current_user.id,
            skill_name=skill_data.skill_name,
            verification_level=skill_data.verification_level,
            evidence_urls=skill_data.evidence_urls or [],
            evidence_description=skill_data.evidence_description,
            skill_level=skill_data.skill_level,
            assessment_date=datetime.now().date(),
            is_verified=skill_data.verification_level == 1,  # Auto-verified for level 1
            verification_status="active"
        )
        
        db.add(student_skill)
        db.commit()
        db.refresh(student_skill)
        
        logger.info(f"Skill added: {skill_data.skill_name} for {current_user.email}")
        
        return student_skill
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add skill: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add skill: {str(e)}"
        )

@app.post("/api/skills/verify/{student_skill_id}", response_model=SkillVerificationResponse, tags=["Skills"])
async def verify_student_skill(
    student_skill_id: uuid.UUID,
    verification_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify a student skill (lecturer only)"""
    if current_user.role != UserRole.LECTURER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lecturers can verify skills"
        )
    
    try:
        student_skill = db.query(StudentSkill).filter(
            StudentSkill.id == student_skill_id
        ).first()
        
        if not student_skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student skill not found"
            )
        
        # Update verification
        student_skill.verified_by = current_user.id
        student_skill.verification_method = verification_data.get("method", "lecturer_assessment")
        student_skill.skill_level = verification_data.get("skill_level", "intermediate")
        student_skill.confidence_score = verification_data.get("confidence_score", 1.0)
        student_skill.is_verified = True
        student_skill.verification_level = 1  # Lecturer verified
        student_skill.updated_at = datetime.now()
        
        db.commit()
        db.refresh(student_skill)
        
        logger.info(f"Skill verified: {student_skill.skill_name} by {current_user.email}")
        
        return student_skill
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to verify skill: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify skill: {str(e)}"
        )

# ==================== NOTIFICATION ENDPOINTS ====================
@app.get("/api/notifications", response_model=List[NotificationResponse], tags=["Notifications"])
async def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get user notifications"""
    try:
        query = db.query(Notification).filter(
            Notification.user_id == current_user.id
        )
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        # Order by creation date (newest first)
        query = query.order_by(Notification.created_at.desc())
        
        # Pagination
        total = query.count()
        notifications = query.offset((page - 1) * limit).limit(limit).all()
        
        return {
            "data": notifications,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            },
            "unread_count": db.query(Notification).filter(
                Notification.user_id == current_user.id,
                Notification.is_read == False
            ).count()
        }
        
    except Exception as e:
        logger.error(f"Failed to get notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notifications"
        )

@app.put("/api/notifications/{notification_id}/read", tags=["Notifications"])
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        notification.mark_as_read()
        db.commit()
        
        return {"message": "Notification marked as read"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to mark notification as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read"
        )

@app.put("/api/notifications/mark-all-read", tags=["Notifications"])
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    try:
        db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        ).update({"is_read": True, "read_at": datetime.now()})
        
        db.commit()
        
        return {"message": "All notifications marked as read"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to mark all notifications as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark all notifications as read"
        )

# ==================== DASHBOARD ENDPOINTS ====================
@app.get("/api/dashboard/student", tags=["Dashboard"])
async def get_student_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get student dashboard data"""
    if current_user.role != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access student dashboard"
        )
    
    try:
        # Get statistics
        total_applications = db.query(Application).filter(
            Application.student_id == current_user.id
        ).count()
        
        accepted_applications = db.query(Application).filter(
            Application.student_id == current_user.id,
            Application.status == ApplicationStatus.ACCEPTED.value
        ).count()
        
        pending_applications = db.query(Application).filter(
            Application.student_id == current_user.id,
            Application.status.in_([
                ApplicationStatus.PENDING.value,
                ApplicationStatus.REVIEWING.value
            ])
        ).count()
        
        completed_projects = db.query(ProjectCompletion).filter(
            ProjectCompletion.student_id == current_user.id
        ).count()
        
        verified_skills = db.query(StudentSkill).filter(
            StudentSkill.student_id == current_user.id,
            StudentSkill.is_verified == True
        ).count()
        
        # Get recent applications
        recent_applications = db.query(Application).filter(
            Application.student_id == current_user.id
        ).order_by(Application.applied_at.desc()).limit(5).all()
        
        # Get recommended projects (simplified)
        recommended_projects = db.query(Project).filter(
            Project.status == ProjectStatus.PUBLISHED.value,
            Project.application_deadline > datetime.now()
        ).order_by(Project.created_at.desc()).limit(5).all()
        
        # Get unread notifications count
        unread_notifications = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        ).count()
        
        return {
            "statistics": {
                "total_applications": total_applications,
                "accepted_applications": accepted_applications,
                "pending_applications": pending_applications,
                "completed_projects": completed_projects,
                "verified_skills": verified_skills,
                "profile_completion": current_user.profile_completion_percentage,
                "unread_notifications": unread_notifications
            },
            "recent_applications": [app.to_dict(include_project=True) for app in recent_applications],
            "recommended_projects": [project.to_dict() for project in recommended_projects],
            "profile": current_user.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to get student dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get student dashboard"
        )

@app.get("/api/dashboard/lecturer", tags=["Dashboard"])
async def get_lecturer_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get lecturer dashboard data"""
    if current_user.role != UserRole.LECTURER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lecturers can access lecturer dashboard"
        )
    
    try:
        # Get statistics
        total_projects = db.query(Project).filter(
            Project.lecturer_id == current_user.id
        ).count()
        
        active_projects = db.query(Project).filter(
            Project.lecturer_id == current_user.id,
            Project.status == ProjectStatus.PUBLISHED.value
        ).count()
        
        ongoing_projects = db.query(Project).filter(
            Project.lecturer_id == current_user.id,
            Project.status == ProjectStatus.IN_PROGRESS.value
        ).count()
        
        total_applications = db.query(Application).join(Project).filter(
            Project.lecturer_id == current_user.id
        ).count()
        
        pending_applications = db.query(Application).join(Project).filter(
            Project.lecturer_id == current_user.id,
            Application.status.in_([
                ApplicationStatus.PENDING.value,
                ApplicationStatus.REVIEWING.value
            ])
        ).count()
        
        students_mentored = db.query(ProjectCompletion).filter(
            ProjectCompletion.lecturer_id == current_user.id
        ).distinct(ProjectCompletion.student_id).count()
        
        skills_verified = db.query(StudentSkill).filter(
            StudentSkill.verified_by == current_user.id
        ).count()
        
        # Get recent projects
        recent_projects = db.query(Project).filter(
            Project.lecturer_id == current_user.id
        ).order_by(Project.created_at.desc()).limit(5).all()
        
        # Get pending applications
        pending_apps = db.query(Application).join(Project).filter(
            Project.lecturer_id == current_user.id,
            Application.status == ApplicationStatus.PENDING.value
        ).order_by(Application.applied_at.desc()).limit(5).all()
        
        # Get unread notifications count
        unread_notifications = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        ).count()
        
        return {
            "statistics": {
                "total_projects": total_projects,
                "active_projects": active_projects,
                "ongoing_projects": ongoing_projects,
                "total_applications": total_applications,
                "pending_applications": pending_applications,
                "students_mentored": students_mentored,
                "skills_verified": skills_verified,
                "profile_completion": current_user.profile_completion_percentage,
                "unread_notifications": unread_notifications
            },
            "recent_projects": [project.to_dict() for project in recent_projects],
            "pending_applications": [app.to_dict(include_student=True) for app in pending_apps],
            "profile": current_user.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to get lecturer dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get lecturer dashboard"
        )

# ==================== ERROR HANDLERS ====================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Internal server error",
            "path": request.url.path,
            "method": request.method
        }
    )

# ==================== RUN APPLICATION ====================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )