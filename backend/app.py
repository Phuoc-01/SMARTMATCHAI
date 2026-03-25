import os
import uuid
import jwt
import datetime
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from dotenv import load_dotenv
import numpy as np
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None
import logging
import traceback
from sqlalchemy import text
from collections import Counter


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'smart-match-ai-secret-key-2025')
db_uri = os.getenv('DATABASE_URL')
if not db_uri:
    raise RuntimeError("DATABASE_URL environment variable is required. Set it to your PostgreSQL connection string.")
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQL Alchemy connection pooling configuration - database-specific
if db_uri.startswith('sqlite'):
    # SQLite doesn't support connection pooling
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
    }
else:
    # PostgreSQL-specific options
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 3600,  # Recycle connections every hour
        'pool_pre_ping': True,  # Test connection before using it
        'echo': False,  # Set to True for SQL debugging
        'connect_args': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30 second statement timeout
        }
    }

# Initialize extensions
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:8080", "http://localhost:8000", "null"])
db = SQLAlchemy(app)

# ==================== DEBUG HELPERS ====================
def log_database_url():
    """Safely log database connection details without exposing password"""
    try:
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'NOT SET')
        # Mask password in logs
        if '@' in db_url:
            parts = db_url.split('@')
            masked = parts[0].split('://')[0] + '://***:***' + '@' + parts[1]
            logger.info(f"Database URL: {masked}")
        else:
            logger.info(f"Database URL: {db_url}")
    except Exception as e:
        logger.error(f"Error logging database URL: {e}")

def verify_database_connection():
    """Verify database connection is working"""
    try:
        result = db.session.execute(text("SELECT 1"))
        logger.info("✅ Database connection verified: OK")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

VECTOR_DIM = 384
VECTOR_TYPE = Vector(VECTOR_DIM) if Vector else db.PickleType

# ==================== MODELS ====================
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # student, lecturer, admin
    student_id = db.Column(db.String(50), unique=True)
    faculty = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    
    # Student specific
    skills = db.Column(db.ARRAY(db.String), nullable=True)
    research_interests = db.Column(db.ARRAY(db.String), nullable=True)
    skill_vector = db.Column(VECTOR_TYPE, nullable=False, default=lambda: [0.0] * VECTOR_DIM)
    gpa = db.Column(db.Numeric(3, 2))
    year_of_study = db.Column(db.Integer)

    @property
    def name(self):
        return self.full_name

    @name.setter
    def name(self, value):
        self.full_name = value
    
    # Lecturer specific
    position = db.Column(db.String(100))
    department = db.Column(db.String(100))
    research_fields = db.Column(db.ARRAY(db.String))
    
    # Common
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    projects = db.relationship('Project', backref='lecturer', lazy=True)
    applications = db.relationship('Application', foreign_keys='Application.student_id', backref='student', lazy=True)
    reviews = db.relationship('Application', foreign_keys='Application.reviewed_by', backref='reviewer', lazy=True)
    verifications = db.relationship('VerifiedSkill', foreign_keys='VerifiedSkill.student_id', backref='student', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'student_id': self.student_id,
            'faculty': self.faculty,
            'phone': self.phone,
            'skills': self.skills or [],
            'research_interests': self.research_interests or [],
            'gpa': float(self.gpa) if self.gpa else None,
            'year_of_study': self.year_of_study,
            'position': self.position,
            'department': self.department,
            'research_fields': self.research_fields or [],
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=False)
    research_field = db.Column(db.String(100))
    required_skills = db.Column(db.PickleType)
    preferred_skills = db.Column(db.PickleType)
    difficulty_level = db.Column(db.String(20), default='medium')
    duration_weeks = db.Column(db.Integer)
    max_students = db.Column(db.Integer, default=1)
    
    # AI matching fields
    requirement_vector = db.Column(VECTOR_TYPE)
    keywords = db.Column(db.PickleType)
    
    # Status
    status = db.Column(db.String(20), default='open')
    
    # Metadata
    lecturer_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deadline = db.Column(db.Date)
    is_public = db.Column(db.Boolean, default=True)
    
    # Relationships
    applications = db.relationship('Application', backref='project', lazy=True)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'title': self.title,
            'description': self.description,
            'research_field': self.research_field,
            'required_skills': self.required_skills or [],
            'preferred_skills': self.preferred_skills or [],
            'difficulty_level': self.difficulty_level,
            'duration_weeks': self.duration_weeks,
            'max_students': self.max_students,
            'status': self.status,
            'lecturer_id': str(self.lecturer_id),
            'lecturer_name': self.lecturer.name if self.lecturer else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'is_public': self.is_public
        }

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False)
    
    # AI matching score
    match_score = db.Column(db.Numeric(5, 2), default=0)
    match_details = db.Column(db.JSON)
    
    # Application status
    status = db.Column(db.String(20), default='pending')
    
    # Additional info
    application_text = db.Column(db.Text)
    applied_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    __table_args__ = (db.UniqueConstraint('student_id', 'project_id'),)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'student_id': str(self.student_id),
            'project_id': str(self.project_id),
            'match_score': float(self.match_score) if self.match_score else 0,
            'match_details': self.match_details,
            'status': self.status,
            'application_text': self.application_text,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'student_name': self.student.name if self.student else None,
            'student_skills': self.student.skills if self.student else [],
            'project_title': self.project.title if self.project else None
        }

class VerifiedSkill(db.Model):
    __tablename__ = 'verified_skills'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    skill = db.Column(db.String(100), nullable=False)
    verified_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    project_id = db.Column(db.String(36))
    verification_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    evidence = db.Column(db.Text)
    level = db.Column(db.String(20))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'skill': self.skill,
            'level': self.level,
            'verification_date': self.verification_date.isoformat() if self.verification_date else None,
            'evidence': self.evidence,
            'verified_by': str(self.verified_by)
        }

# ==================== AI MODEL INTEGRATION ====================
try:
    from sentence_transformers import SentenceTransformer
    has_ai_model = True
except Exception as e:
    logger.error(f"Failed to import sentence_transformers: {e}")
    has_ai_model = False

class AIMatchingEngine:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        try:
            if has_ai_model:
                logger.info(f"🔄 Loading AI model: {model_name}")
                self.model = SentenceTransformer(model_name)
                logger.info("✅ AI model loaded successfully")
            else:
                logger.warning("⚠️ sentence-transformers not installed or failed to load. Using fallback embeddings.")
                self.model = None
        except Exception as e:
            logger.error(f"Failed to initialize AI engine: {e}")
            self.model = None

    def get_embedding(self, text):
        """Convert text to vector embedding"""
        try:
            if isinstance(text, list):
                text = ' '.join(text)
            if not text or text.strip() == '':
                return np.zeros(VECTOR_DIM).tolist()
            if self.model:
                vec = self.model.encode(text, convert_to_numpy=True)
                return vec.tolist()
            # Fallback random deterministic vector for local runs
            vec = np.array([hash(text + str(i)) % 100 / 100 for i in range(VECTOR_DIM)], dtype=float)
            norm = np.linalg.norm(vec)
            return (vec / (norm + 1e-9)).tolist()
        except Exception as e:
            logger.error(f"Error generating embedding for text '{text[:50]}...': {e}")
            return np.zeros(VECTOR_DIM).tolist()
    
    def calculate_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = np.dot(vec1, vec2) / (norm1 * norm2)
        # Convert to percentage (0-100)
        return float(max(0, min(100, similarity * 100)))
    
    def _normalize_vector(self, vec):
        if vec is None:
            return None
        if isinstance(vec, (np.ndarray, list, tuple)):
            return np.asarray(vec, dtype=float)
        if isinstance(vec, (bytes, bytearray)):
            try:
                vec = vec.decode('utf-8')
            except Exception:
                raise ValueError('Cannot decode vector bytes')
        if isinstance(vec, str):
            text = vec.strip()
            if text.startswith('[') and text.endswith(']'):
                text = text[1:-1]
            return np.fromstring(text, sep=',', dtype=float)
        try:
            return np.asarray(list(vec), dtype=float)
        except Exception as e:
            raise ValueError(f'Invalid vector type: {type(vec)} ({e})')

    def compute_score(self, student, project):
        """Calculate match score between student and project (0-1 scale)"""

        # Ensure student vector exists
        if not student.skill_vector or (isinstance(student.skill_vector, (list, tuple)) and np.linalg.norm(np.array(student.skill_vector)) == 0):
            fallback_student_text = []
            if student.skills:
                fallback_student_text.extend(student.skills if isinstance(student.skills, list) else [str(student.skills)])
            if student.research_interests:
                fallback_student_text.extend(student.research_interests if isinstance(student.research_interests, list) else [str(student.research_interests)])
            if student.faculty:
                fallback_student_text.append(str(student.faculty))
            if student.name:
                fallback_student_text.append(str(student.name))
            if fallback_student_text:
                student.skill_vector = self.get_embedding(' '.join(fallback_student_text))

        # Ensure project vector exists
        if not project.requirement_vector or (isinstance(project.requirement_vector, (list, tuple)) and np.linalg.norm(np.array(project.requirement_vector)) == 0):
            fallback_project_text = [project.title or '', project.description or '']
            if project.required_skills:
                fallback_project_text.extend(project.required_skills if isinstance(project.required_skills, list) else [str(project.required_skills)])
            if project.preferred_skills:
                fallback_project_text.extend(project.preferred_skills if isinstance(project.preferred_skills, list) else [str(project.preferred_skills)])
            if project.research_field:
                fallback_project_text.append(str(project.research_field))
            if any(fallback_project_text):
                project.requirement_vector = self.get_embedding(' '.join(filter(None, fallback_project_text)))

        try:
            student_vec = self._normalize_vector(student.skill_vector)
            project_vec = self._normalize_vector(project.requirement_vector)
        except Exception as e:
            logger.error(f"Vector normalization error: {e}")
            return 0.0

        if student_vec is None or project_vec is None:
            return 0.0

        if student_vec.size != VECTOR_DIM or project_vec.size != VECTOR_DIM:
            logger.warning(f"Vector size mismatch: student {student_vec.size}, project {project_vec.size}")
            return 0.0

        # Cosine similarity (0-1 scale)
        cosine_sim = self.calculate_similarity(student_vec, project_vec) / 100.0

        # Skill overlap score
        overlap = 0.0
        if student.skills and project.required_skills:
            student_skills = set(student.skills) if isinstance(student.skills, list) else set()
            project_skills = set(project.required_skills) if isinstance(project.required_skills, list) else set()
            intersection = student_skills & project_skills
            if project_skills:
                overlap = len(intersection) / len(project_skills)

        # Final score: 0.7 * cosine_similarity + 0.3 * overlap
        final_score = 0.7 * cosine_sim + 0.3 * overlap

        logger.info(
            f"compute_score: student={student.id if hasattr(student, 'id') else 'N/A'} project={project.id if hasattr(project, 'id') else 'N/A'} "
            f"cosine_sim={cosine_sim:.4f} overlap={overlap:.4f} final_score={final_score:.4f}"
        )

        return round(final_score, 3)
    
    def explain_match(self, student, project):
        """Generate explanation for the match"""
        explanations = []
        
        # Find matching skills
        if student.skills and project.required_skills:
            student_skills = set(student.skills) if isinstance(student.skills, list) else set()
            project_skills = set(project.required_skills) if isinstance(project.required_skills, list) else set()
            matching_skills = student_skills & project_skills
            
            if matching_skills:
                explanations.append(f"Matching skills: {', '.join(matching_skills)}")
            else:
                explanations.append("No direct skill matches found")
        
        # Add interest alignment
        if student.research_interests and project.research_field:
            student_interests = set(student.research_interests) if isinstance(student.research_interests, list) else set()
            if project.research_field.lower() in ' '.join(student_interests).lower():
                explanations.append(f"Your interests align with {project.research_field} field")
        
        if not explanations:
            explanations.append("Match based on semantic similarity of profiles")
        
        return "You match this project because:\n" + "\n".join(f"* {exp}" for exp in explanations)
    
    def match_student_to_project(self, student, project):
        """Calculate match score between student and project (legacy method for compatibility)"""
        score = self.compute_score(student, project)
        explanation = self.explain_match(student, project)
        
        match_details = {
            'score': score,
            'explanation': explanation,
            'cosine_similarity': score * 0.7 / 0.7 if score > 0 else 0,  # Approximate
            'skill_overlap': score * 0.3 / 0.3 if score > 0 else 0     # Approximate
        }
        
        return score * 100, match_details  # Return 0-100 for backward compatibility

# Initialize AI engine
ai_engine = None

# ==================== AUTHENTICATION ====================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
            g.current_user = current_user
        except Exception:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.role not in roles:
                return jsonify({'message': 'Permission denied!'}), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator

# ==================== AUTH ROUTES ====================
@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    ==================== PRODUCTION REGISTRATION ROUTE ====================
    
    Matches the unified users table schema with:
    - UUID primary key
    - Unified student/lecturer fields
    - Vector(384) skill_vector column
    - Proper error handling and logging
    
    =========================================================================
    """
    
    logger.info("=" * 100)
    logger.info("🔵 REGISTRATION REQUEST STARTED")
    logger.info("=" * 100)
    
    try:
        # ============ REQUEST PARSING ============
        logger.info("📥 Parsing incoming JSON request...")
        data = request.get_json()
        # new_user_uuid = uuid.uuid4()
        
        if not data:
            logger.error("❌ Request body is empty")
            return jsonify({'error': 'Request body is empty'}), 400
        
        logger.info(f"📊 Raw request data keys: {list(data.keys())}")
        
        # ============ FIELD EXTRACTION ============
        # Extract with flexible field names (handle both 'name' and 'full_name')
        full_name = data.get('full_name') or data.get('name')
        email = (data.get('email', '') or '').lower().strip()
        password = data.get('password')
        role = (data.get('role', '') or '').lower().strip()
        
        logger.info(f"📋 Extracted fields:")
        logger.info(f"   - full_name: {'✓' if full_name else '✗ MISSING'}")
        logger.info(f"   - email: {email if email else '✗ MISSING'}")
        logger.info(f"   - password: {'✓ (len={len(password)})' if password else '✗ MISSING'}")
        logger.info(f"   - role: {role if role in ['student', 'lecturer'] else f'✗ INVALID ({role})'}")
        
        # ============ VALIDATION ============
        if not full_name:
            logger.error("❌ Validation failed: full_name is required")
            return jsonify({'error': 'Name is required'}), 400
        
        if not email:
            logger.error("❌ Validation failed: email is required")
            return jsonify({'error': 'Email is required'}), 400
        
        if not password or len(password) < 6:
            logger.error("❌ Validation failed: password must be at least 6 characters")
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        if role not in ['student', 'lecturer']:
            logger.error(f"❌ Validation failed: invalid role '{role}'")
            return jsonify({'error': 'Role must be "student" or "lecturer"'}), 400
        
        logger.info("✅ All required fields validated")
        
        # ============ DATABASE CHECKS ============
        logger.info(f"🔍 Checking if email '{email}' already exists...")
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            logger.warning(f"⚠️ Email '{email}' already registered (user_id: {existing_user.id})")
            return jsonify({'error': 'Email already registered'}), 409
        
        logger.info(f"✅ Email '{email}' is available")
        
        # ============ UUID GENERATION ============
        new_user_id = uuid.uuid4()
        logger.info(f"🆔 Generated UUID: {new_user_id}")
        
        # ============ USER OBJECT CREATION ============
        logger.info("🔨 Creating user object...")
        
        # Cast skill_vector to list of floats explicitly for pgvector compatibility
        zero_vector = [float(0.0)] * VECTOR_DIM

        user = User(
            id=new_user_id,
            email=email,
            full_name=full_name,
            role=role,
            skill_vector=zero_vector
        )
        
        # Hash password BEFORE saving
        user.set_password(password)
        logger.info(f"🔐 Password hashed and set")
        
        # ============ ROLE-SPECIFIC FIELD MAPPING ============
        if role == 'student':
            logger.info("📚 Processing STUDENT-specific fields...")
            user.student_id = data.get('student_id')
            user.faculty = data.get('faculty')
            user.skills = data.get('skills', [])
            user.research_interests = data.get('research_interests', [])
            user.year_of_study = data.get('year_of_study')
            
            logger.info(f"   ✓ student_id: {user.student_id}")
            logger.info(f"   ✓ faculty: {user.faculty}")
            logger.info(f"   ✓ skills: {len(user.skills)} items")
            logger.info(f"   ✓ year_of_study: {user.year_of_study}")
            
        elif role == 'lecturer':
            logger.info("👨‍🏫 Processing LECTURER-specific fields...")
            user.position = data.get('position')
            user.department = data.get('department')
            user.research_fields = data.get('research_fields') or []
            # Lecturers still need these ARRAY fields initialized (nullable=True but safer explicit)
            user.skills = []
            user.research_interests = []
            
            logger.info(f"   ✓ position: {user.position}")
            logger.info(f"   ✓ department: {user.department}")
            logger.info(f"   ✓ research_fields: {len(user.research_fields)} items")
        
        logger.info("✅ User object created and populated")
        
        # ============ DATABASE COMMIT ============
        logger.info("💾 PREPARING DATABASE COMMIT...")
        logger.info(f"   Session state BEFORE add: {db.session.is_active}")
        logger.info(f"   Pending new objects: {len(db.session.new)}")
        
        db.session.add(user)
        logger.info(f"✅ User added to session")
        logger.info(f"   Pending new objects AFTER add: {len(db.session.new)}")
        
        logger.info("⏳ EXECUTING db.session.commit()...")
        try:
            db.session.commit()
        except IntegrityError as ie:
            db.session.rollback()
            logger.warning("⚠️ IntegrityError during register (duplicate field?)", exc_info=ie)
            error_msg = str(ie.orig) if hasattr(ie, 'orig') else str(ie)
            if 'student_id' in error_msg.lower() or 'unique' in error_msg.lower():
                return jsonify({'error': 'Duplicate student_id or email'}), 409
            return jsonify({'error': 'Integrity error', 'details': error_msg}), 409
        logger.info("✅ ✅ ✅ COMMIT SUCCESSFUL ✅ ✅ ✅")
        
        logger.info(f"   User ID: {user.id}")
        logger.info(f"   Email: {user.email}")
        logger.info(f"   Role: {user.role}")
        logger.info(f"   Session state AFTER commit: {db.session.is_active}")
        
        # ============ VERIFICATION QUERY ============
        logger.info("🔎 Verifying user was saved to database...")
        saved_user = User.query.filter_by(email=email).first()
        
        if saved_user:
            logger.info(f"✅ ✅ VERIFICATION SUCCESSFUL ✅ ✅")
            logger.info(f"   User found in database with ID: {saved_user.id}")
            logger.info(f"   Name: {saved_user.full_name}")
            logger.info(f"   Role: {saved_user.role}")
            logger.info(f"   Created at: {saved_user.created_at}")
        else:
            logger.error(f"❌ ❌ VERIFICATION FAILED ❌ ❌")
            logger.error(f"   User NOT FOUND in database after commit!")
            logger.error(f"   This should never happen - commit success but query returns nothing")
            return jsonify({'error': 'User registration failed during verification'}), 500
        
        # ============ JWT TOKEN GENERATION ============
        logger.info("🔐 Generating JWT token...")
        token = jwt.encode({
            'user_id': str(user.id),
            'email': user.email,
            'role': user.role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        logger.info("✅ JWT token generated")
        
        # ============ RESPONSE ============
        logger.info("=" * 100)
        logger.info("🟢 REGISTRATION SUCCESSFUL - RETURNING 201 RESPONSE")
        logger.info("=" * 100)
        
        return jsonify({
            'message': 'Registration successful',
            'token': token,
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        logger.error("=" * 100)
        logger.error("🔴 🔴 🔴 REGISTRATION FAILED - EXCEPTION OCCURRED 🔴 🔴 🔴")
        logger.error("=" * 100)
        logger.error(f"Exception Type: {type(e).__name__}")
        logger.error(f"Exception Message: {str(e)}")
        logger.error(f"Full Traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 100)
        
        # Attempt rollback to clean up session
        try:
            logger.info("⏳ Attempting db.session.rollback() to clean up...")
            db.session.rollback()
            logger.info("✅ Rollback successful - session cleaned")
        except Exception as rollback_error:
            logger.error(f"❌ Rollback also failed: {rollback_error}")
        
        return jsonify({
            'error': 'Registration failed',
            'details': str(e),
            'exception_type': type(e).__name__
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'message': 'Missing email or password'}), 400
        
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'message': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'message': 'Account is deactivated'}), 403
        
        # Generate token
        token = jwt.encode({
            'user_id': str(user.id),
            'email': user.email,
            'role': user.role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# ==================== STUDENT ROUTES ====================
@app.before_request
def enforce_student_jwt():
    # Protect all student routes with JWT
    if request.path.startswith('/api/student') and request.method != 'OPTIONS':
        # allow /api/student/<student_id> only with token
        auth_header = request.headers.get('Authorization', '')
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data.get('user_id'))
            if not current_user:
                return jsonify({'message': 'Invalid user token'}), 401
            g.current_user = current_user
        except Exception:
            return jsonify({'message': 'Token is invalid!'}), 401

@app.route('/api/student/profile', methods=['GET'])
@token_required
@role_required(['student'])
def get_student_profile(current_user):
    try:
        profile = current_user.to_dict()
        
        # Get verified skills
        verified_skills = VerifiedSkill.query.filter_by(student_id=current_user.id).all()
        profile['verified_skills'] = [skill.to_dict() for skill in verified_skills]
        
        # Get applications
        applications = Application.query.filter_by(student_id=current_user.id).all()
        profile['applications'] = [app.to_dict() for app in applications]
        
        return jsonify(profile)
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/student/applications', methods=['GET'])
@token_required
@role_required(['student'])
def get_student_applications(current_user):
    try:
        applications = Application.query.filter_by(student_id=current_user.id).order_by(Application.applied_at.desc()).all()
        return jsonify({
            'applications': [app.to_dict() for app in applications],
            'count': len(applications)
        })
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/student/profile', methods=['PUT'])
@token_required
@role_required(['student'])
def update_student_profile(current_user):
    try:
        data = request.json
        
        # Update basic info
        if 'name' in data:
            current_user.name = data['name']
        if 'faculty' in data:
            current_user.faculty = data['faculty']
        if 'phone' in data:
            current_user.phone = data['phone']
        if 'gpa' in data:
            current_user.gpa = data['gpa']
        if 'year_of_study' in data:
            current_user.year_of_study = data['year_of_study']
        
        # Update skills and research interests
        if 'skills' in data or 'research_interests' in data:
            # Update skill vector for AI matching using combined text
            student_text = []
            if data.get('skills'):
                student_text.append(' '.join(data['skills']) if isinstance(data['skills'], list) else str(data['skills']))
            if data.get('research_interests'):
                student_text.append(' '.join(data['research_interests']) if isinstance(data['research_interests'], list) else str(data['research_interests']))
            if student_text:
                current_user.skill_vector = ai_engine.get_embedding(' '.join(student_text))
        
        if 'skills' in data:
            current_user.skills = data['skills']
        
        if 'research_interests' in data:
            current_user.research_interests = data['research_interests']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': current_user.to_dict()
        })
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/student/apply', methods=['POST'])
@token_required
@role_required(['student'])
def apply_student_api(current_user):
    data = request.json or {}
    project_id = data.get('project_id')
    if not project_id:
        return jsonify({'message': 'Missing project_id'}), 400
    return apply_to_project(current_user, project_id)

@app.route('/api/student/<student_id>', methods=['GET'])
@token_required
def get_student_by_id(current_user, student_id):
    try:
        user = User.query.get(student_id)
        if not user:
            return jsonify({'message': 'Student not found'}), 404
        if user.role != 'student':
            return jsonify({'message': 'User is not a student'}), 400
        return jsonify(user.to_dict())
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/student/projects/recommended', methods=['GET'])
@token_required
@role_required(['student'])
def get_recommended_projects(current_user):
    try:
        # Refresh user vector if missing
        if not current_user.skill_vector or (isinstance(current_user.skill_vector, (list, tuple)) and np.linalg.norm(np.array(current_user.skill_vector)) == 0):
            refresh_text = []
            if current_user.skills:
                refresh_text.extend(current_user.skills if isinstance(current_user.skills, list) else [str(current_user.skills)])
            if current_user.research_interests:
                refresh_text.extend(current_user.research_interests if isinstance(current_user.research_interests, list) else [str(current_user.research_interests)])
            if current_user.faculty:
                refresh_text.append(str(current_user.faculty))
            if current_user.name:
                refresh_text.append(str(current_user.name))
            if refresh_text:
                current_user.skill_vector = ai_engine.get_embedding(' '.join(filter(None, refresh_text)))
                db.session.commit()
                app.logger.info('Updated missing student skill_vector for user %s', current_user.email)

        # Get open and public projects
        projects = Project.query.filter_by(status='open', is_public=True).all()

        recommendations = []
        for project in projects:
            # Refresh project vector if missing
            if not project.requirement_vector or (isinstance(project.requirement_vector, (list, tuple)) and np.linalg.norm(np.array(project.requirement_vector)) == 0):
                project_text = ' '.join(filter(None, [project.title, project.description, ' '.join(project.required_skills or []), ' '.join(project.preferred_skills or []), project.research_field or '']))
                project.requirement_vector = ai_engine.get_embedding(project_text)
                db.session.commit()
                app.logger.info('Updated missing requirement_vector for project %s', project.title)

            score = ai_engine.compute_score(current_user, project)
            explanation = ai_engine.explain_match(current_user, project)

            app.logger.info('Recommendation - user %s project %s score=%.3f', current_user.email, project.title, score)

            project_data = project.to_dict()
            project_data['score'] = score
            project_data['explanation'] = explanation

            application = Application.query.filter_by(student_id=current_user.id, project_id=project.id).first()
            project_data['has_applied'] = bool(application)
            project_data['application_status'] = application.status if application else None

            recommendations.append(project_data)

        recommendations.sort(key=lambda x: x.get('score', 0), reverse=True)

        return jsonify({'recommendations': recommendations, 'count': len(recommendations)})
    except Exception as e:
        app.logger.exception('Error in /api/student/projects/recommended')
        return jsonify({'message': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/api/student/projects/<project_id>/apply', methods=['POST'])
@token_required
@role_required(['student'])
def apply_to_project(current_user, project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'message': 'Project not found'}), 404
        
        if project.status != 'open':
            return jsonify({'message': 'Project is not accepting applications'}), 400
        
        # Check if already applied
        existing_application = Application.query.filter_by(
            student_id=current_user.id,
            project_id=project.id
        ).first()
        
        if existing_application:
            return jsonify({'message': 'Already applied to this project'}), 400
        
        # Calculate match score
        match_score, match_details = ai_engine.match_student_to_project(current_user, project)
        
        # Create application
        application_text = ''
        if request.json and isinstance(request.json, dict):
            application_text = request.json.get('application_text', '')
        application = Application(
            student_id=current_user.id,
            project_id=project.id,
            match_score=match_score,
            match_details=match_details,
            application_text=application_text,
            status='pending'
        )
        
        db.session.add(application)
        db.session.commit()
        
        return jsonify({
            'message': 'Application submitted successfully',
            'application': application.to_dict()
        })
    except Exception as e:
        app.logger.exception('Error applying to project')
        return jsonify({'message': str(e)}), 500

# ==================== LECTURER ROUTES ====================
@app.route('/api/lecturer/profile', methods=['GET'])
@token_required
@role_required(['lecturer'])
def get_lecturer_profile(current_user):
    """Return the lecturer's own full profile."""
    try:
        profile = current_user.to_dict()
        # Add projects summary
        projects = Project.query.filter_by(lecturer_id=current_user.id).all()
        profile['projects_count'] = len(projects)
        profile['open_projects']  = len([p for p in projects if p.status == 'open'])
        return jsonify(profile)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/lecturer/profile', methods=['PUT'])
@token_required
@role_required(['lecturer'])
def update_lecturer_profile(current_user):
    """Update the lecturer's own profile fields."""
    try:
        data = request.json or {}
        if 'name' in data or 'full_name' in data:
            current_user.full_name = data.get('full_name') or data.get('name')
        if 'position' in data:
            current_user.position = data['position']
        if 'department' in data:
            current_user.department = data['department']
        if 'phone' in data:
            current_user.phone = data['phone']
        if 'research_fields' in data:
            current_user.research_fields = data['research_fields']
        db.session.commit()
        # Update cached representation
        updated = current_user.to_dict()
        return jsonify({'message': 'Profile updated successfully', 'user': updated})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500


@app.route('/api/lecturer/projects', methods=['POST'])
@token_required
@role_required(['lecturer'])
def create_project(current_user):
    try:
        data = request.json
        
        required_fields = ['title', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        # Create project
        deadline_val = data.get('deadline')
        app.logger.info(f"create_project received deadline={deadline_val} ({type(deadline_val)})")
        if isinstance(deadline_val, str):
            try:
                deadline_val = datetime.datetime.strptime(deadline_val, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'message': 'deadline must be in YYYY-MM-DD format'}), 400
        project = Project(
            title=data['title'],
            description=data['description'],
            research_field=data.get('research_field'),
            required_skills=data.get('required_skills', []),
            preferred_skills=data.get('preferred_skills', []),
            difficulty_level=data.get('difficulty_level', 'medium'),
            duration_weeks=data.get('duration_weeks'),
            max_students=data.get('max_students', 1),
            lecturer_id=current_user.id,
            deadline=deadline_val,
            is_public=data.get('is_public', True)
        )
        
        # Generate requirement vector for AI matching
        project_text = data['description']
        if data.get('required_skills'):
            project_text += ' ' + ' '.join(data['required_skills'])
        project.requirement_vector = ai_engine.get_embedding(project_text)
        
        db.session.add(project)
        db.session.commit()
        
        return jsonify({
            'message': 'Project created successfully',
            'project': project.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/lecturer/projects', methods=['GET'])
@token_required
@role_required(['lecturer'])
def get_lecturer_projects(current_user):
    try:
        projects = Project.query.filter_by(lecturer_id=current_user.id).all()
        
        projects_data = []
        for project in projects:
            project_data = project.to_dict()
            
            # Get applications count
            applications = Application.query.filter_by(project_id=project.id).all()
            project_data['applications_count'] = len(applications)
            project_data['pending_applications'] = len([a for a in applications if a.status == 'pending'])
            
            projects_data.append(project_data)
        
        return jsonify({
            'projects': projects_data,
            'count': len(projects_data)
        })
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/lecturer/projects/<project_id>/applications', methods=['GET'])
@token_required
@role_required(['lecturer'])
def get_project_applications(current_user, project_id):
    try:
        project = Project.query.get(project_id)
        if not project or project.lecturer_id != current_user.id:
            return jsonify({'message': 'Project not found or access denied'}), 404
        
        applications = Application.query.filter_by(project_id=project.id).all()
        
        # Sort by match score (descending)
        applications.sort(key=lambda x: x.match_score or 0, reverse=True)
        
        applications_data = []
        for app in applications:
            app_data = app.to_dict()
            
            # Get student details
            student = User.query.get(app.student_id)
            if student:
                app_data['student'] = student.to_dict()
            
            applications_data.append(app_data)
        
        return jsonify({
            'project': project.to_dict(),
            'applications': applications_data,
            'count': len(applications_data)
        })
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/lecturer/applications/<application_id>/review', methods=['PUT'])
@token_required
@role_required(['lecturer'])
def review_application(current_user, application_id):
    try:
        data = request.json
        if 'status' not in data:
            return jsonify({'message': 'Missing status'}), 400
        
        application = Application.query.get(application_id)
        if not application:
            return jsonify({'message': 'Application not found'}), 404
        
        # Verify lecturer owns the project
        project = Project.query.get(application.project_id)
        if not project or project.lecturer_id != current_user.id:
            return jsonify({'message': 'Access denied'}), 403
        
        # Update application
        application.status = data['status']
        application.reviewed_at = datetime.datetime.utcnow()
        application.reviewed_by = current_user.id
        
        db.session.commit()
        
        return jsonify({
            'message': 'Application updated successfully',
            'application': application.to_dict()
        })
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/lecturer/verify-skills', methods=['POST'])
@token_required
@role_required(['lecturer'])
def verify_student_skills(current_user):
    try:
        data = request.json
        required_fields = ['student_id', 'project_id', 'skills']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        # Create verification records
        for skill_info in data['skills']:
            verified_skill = VerifiedSkill(
                student_id=data['student_id'],
                skill=skill_info['skill'],
                verified_by=current_user.id,
                project_id=data['project_id'],
                level=skill_info.get('level', 'intermediate'),
                evidence=skill_info.get('evidence')
            )
            db.session.add(verified_skill)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Skills verified successfully',
            'verified_count': len(data['skills'])
        })
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# ==================== ADMIN ROUTES ====================
@app.route('/api/admin/stats', methods=['GET'])
@token_required
@role_required(['admin'])
def get_admin_stats(current_user):
    try:
        # User statistics
        total_users = User.query.count()
        students = User.query.filter_by(role='student').count()
        lecturers = User.query.filter_by(role='lecturer').count()
        
        # Project statistics
        total_projects = Project.query.count()
        open_projects = Project.query.filter_by(status='open').count()
        completed_projects = Project.query.filter_by(status='completed').count()
        
        # Application statistics
        total_applications = Application.query.count()
        pending_applications = Application.query.filter_by(status='pending').count()
        accepted_applications = Application.query.filter_by(status='accepted').count()
        
        # Match statistics
        applications_with_match = Application.query.filter(Application.match_score > 0).all()
        avg_match_score = np.mean([app.match_score for app in applications_with_match]) if applications_with_match else 0
        
        return jsonify({
            'user_stats': {
                'total': total_users,
                'students': students,
                'lecturers': lecturers
            },
            'project_stats': {
                'total': total_projects,
                'open': open_projects,
                'completed': completed_projects
            },
            'application_stats': {
                'total': total_applications,
                'pending': pending_applications,
                'accepted': accepted_applications,
                'rejected': total_applications - pending_applications - accepted_applications
            },
            'matching_stats': {
                'average_match_score': round(float(avg_match_score), 2),
                'applications_with_ai_matching': len(applications_with_match)
            }
        })
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# ==================== MISSING ROUTE ALIASES FOR USER REQUIREMENTS ====================
@app.route('/login', methods=['POST'])
def login_plain():
    return login()

@app.route('/register', methods=['POST'])
@app.route('/api/register', methods=['POST'])
def register_compat():
    """Backward-compatible registration endpoint - forwards to /api/auth/register logic"""
    logger.info("📍 Backward-compatible /register route called, forwarding to comprehensive registration logic...")
    # The logic is already in the function above, just call it with a fresh context
    return register()

@app.route('/student/profile', methods=['POST'])
@token_required
@role_required(['student'])
def student_profile_create_or_update(current_user):
    return update_student_profile(current_user)

@app.route('/student/<student_id>', methods=['GET'])
@token_required
def student_profile_by_id(current_user, student_id):
    return get_student_by_id(current_user, student_id)

@app.route('/projects', methods=['GET'])
def list_projects():
    projects = Project.query.filter_by(status='open', is_public=True).all()
    return jsonify({'projects': [p.to_dict() for p in projects]})

@app.route('/apply', methods=['POST'])
@token_required
@role_required(['student'])
def apply_plain(current_user):
    data = request.json or {}
    project_id = data.get('project_id')
    if not project_id:
        return jsonify({'message': 'Missing project_id'}), 400
    return apply_to_project(current_user, project_id)

@app.route('/lecturer/projects', methods=['GET'])
@token_required
@role_required(['lecturer'])
def list_lecturer_projects(current_user):
    return get_lecturer_projects(current_user)

@app.route('/lecturer/applications', methods=['GET'])
@token_required
@role_required(['lecturer'])
def list_lecturer_applications(current_user):
    projects = Project.query.filter_by(lecturer_id=current_user.id).all()
    project_ids = [p.id for p in projects]
    applications = Application.query.filter(Application.project_id.in_(project_ids)).all()
    return jsonify({'applications': [a.to_dict() for a in applications]})

@app.route('/evaluate', methods=['POST'])
@token_required
@role_required(['lecturer'])
def evaluate_plain(current_user):
    data = request.json or {}
    application_id = data.get('application_id')
    status = data.get('status')
    if not application_id or not status:
        return jsonify({'message': 'Missing application_id or status'}), 400
    return review_application(current_user, application_id)

@app.route('/admin/projects', methods=['GET'])
@token_required
@role_required(['admin'])
def admin_get_projects(current_user):
    projects = Project.query.all()
    return jsonify({'projects': [p.to_dict() for p in projects]})

@app.route('/admin/project/<project_id>', methods=['PATCH'])
@token_required
@role_required(['admin'])
def admin_update_project(current_user, project_id):
    data = request.json or {}
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404
    if 'status' in data:
        project.status = data['status']
    if 'is_public' in data:
        project.is_public = data['is_public']
    db.session.commit()
    return jsonify({'message': 'Project updated', 'project': project.to_dict()})

@app.route('/admin/lecturers', methods=['GET'])
@token_required
@role_required(['admin'])
def admin_get_lecturers(current_user):
    lecturers = User.query.filter_by(role='lecturer').all()
    return jsonify({'lecturers': [u.to_dict() for u in lecturers]})

@app.route('/admin/approve', methods=['POST'])
@token_required
@role_required(['admin'])
def admin_approve(current_user):
    data = request.json or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'message': 'Missing user_id'}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    user.is_verified = True
    db.session.commit()
    return jsonify({'message': 'User approved', 'user': user.to_dict()})

@app.route('/admin/reports', methods=['GET'])
@token_required
@role_required(['admin'])
def admin_reports(current_user):
    return get_admin_stats(current_user)

@app.route('/admin/action', methods=['POST'])
@token_required
@role_required(['admin'])
def admin_action(current_user):
    data = request.json or {}
    action = data.get('action')
    if action == 'deactivate_user':
        user_id = data.get('user_id')
        user = User.query.get(user_id) if user_id else None
        if user:
            user.is_active = False
            db.session.commit()
            return jsonify({'message': 'User deactivated', 'user': user.to_dict()})
    return jsonify({'message': 'Action executed'})

@app.route('/admin/skills', methods=['GET'])
@app.route('/api/admin/stats', methods=['GET'])
@token_required
@role_required(['admin'])
def admin_get_stats(current_user):
    try:
        total_students = User.query.filter_by(role='student').count()
        total_projects = Project.query.count()
        total_applications = Application.query.count()

        # derive top skills from student profiles
        all_skills = []
        students = User.query.filter_by(role='student').all()
        for s in students:
            if s.skills:
                all_skills.extend(s.skills if isinstance(s.skills, list) else [str(s.skills)])

        skill_counter = Counter([skill.strip().lower() for skill in all_skills if isinstance(skill, str) and skill.strip()])
        top_skills = [{'skill': skill, 'count': count} for skill, count in skill_counter.most_common(5)]

        return jsonify({
            'total_students': total_students,
            'total_projects': total_projects,
            'total_applications': total_applications,
            'top_skills': top_skills
        })
    except Exception as e:
        app.logger.exception('Error in /api/admin/stats')
        return jsonify({'message': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/api/admin/skills', methods=['GET'])
@token_required
@role_required(['admin'])
def admin_get_skills(current_user):
    skills = db.session.query(VerifiedSkill.skill).distinct().all()
    return jsonify({'skills': [s[0] for s in skills]})

@app.route('/admin/skills', methods=['POST'])
@token_required
@role_required(['admin'])
def admin_add_skill(current_user):
    data = request.json or {}
    skill = data.get('skill')
    student_id = data.get('student_id')
    if not skill or not student_id:
        return jsonify({'message': 'Missing skill or student_id'}), 400
    vs = VerifiedSkill(student_id=student_id, skill=skill, level=data.get('level', 'intermediate'))
    db.session.add(vs)
    db.session.commit()
    return jsonify({'message': 'Skill added', 'skill': vs.to_dict()})

# ==================== HEALTH CHECK ====================
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'SMART-MATCH AI Backend',
        'version': '2.0.0',
        'ai_model': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
        'database': 'connected' if db.session.execute(text("SELECT 1")).first() else 'disconnected',
        'timestamp': datetime.datetime.utcnow().isoformat()
    })

# ==================== MAIN ====================
if __name__ == '__main__':
    with app.app_context():
        logger.info("=" * 80)
        logger.info("🚀 SMART-MATCH AI BACKEND INITIALIZATION")
        logger.info("=" * 80)
        
        # Log database connection details
        logger.info("📊 Database Configuration:")
        log_database_url()
        
        # Verify database connection
        logger.info("🔌 Checking database connection...")
        db_connected = verify_database_connection()
        
        if not db_connected:
            logger.error("❌ Cannot connect to database. Check DATABASE_URL environment variable.")
            logger.error("Expected format: postgresql://username:password@host:port/database")
            raise RuntimeError("Database connection failed")
        
        logger.info("⏳ Creating database tables...")
        db.create_all()
        logger.info("✅ Database tables created")

        logger.info("⏳ Initializing AI engine...")
        ai_engine = AIMatchingEngine()
        logger.info("✅ AI engine ready")
        
        logger.info("=" * 80)
        logger.info("🟢 BACKEND INITIALIZED SUCCESSFULLY")
        logger.info("=" * 80)

    logger.info("🚀 SMART-MATCH AI BACKEND is running on http://0.0.0.0:5000")

    app.run(host='0.0.0.0', port=5000)