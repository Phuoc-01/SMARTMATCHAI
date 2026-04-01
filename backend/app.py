import os
import uuid
import jwt
import datetime
import threading
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError
from functools import wraps
from dotenv import load_dotenv
import numpy as np

from ai_matching import create_ai_matching_service, calculate_match_score
from models import db, User, Project, Application, VerifiedSkill  # type: ignore[attr-defined]
import logging
import traceback
from sqlalchemy import text
from sqlalchemy.orm import joinedload
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
# CORS configuration
# The frontend runs in the user's browser (host network), so allow localhost and
# common private LAN IP ranges. Docker-internal hostnames like "frontend" are
# not resolvable from the browser and don't help here.
CORS(
    app,
    origins=[
        r"http://localhost(:\d+)?",
        r"http://127\.0\.0\.1(:\d+)?",
        r"http://192\.168\.\d+\.\d+(:\d+)?",
        r"http://10\.\d+\.\d+\.\d+(:\d+)?",
        r"http://172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+(:\d+)?",
        "null",
    ],
)
db.init_app(app)
with app.app_context():
    # Tự động tạo 12 bảng dựa trên models.py mới
    db.create_all()
    print("🚀 SMART MATCH AI: Database đã sẵn sàng!")

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

_ai_engine = None
_ai_engine_init_error = None
_ai_engine_next_retry_at = None
_ai_engine_init_in_progress = False
_ai_engine_lock = threading.Lock()


def _init_ai_engine_worker():
    """Background worker to initialize the AI engine without blocking requests."""
    global _ai_engine, _ai_engine_init_error, _ai_engine_next_retry_at, _ai_engine_init_in_progress

    try:
        engine = create_ai_matching_service()
        with _ai_engine_lock:
            _ai_engine = engine
            _ai_engine_init_error = None
            _ai_engine_next_retry_at = None
    except Exception as e:
        now = datetime.datetime.utcnow()
        retry_seconds = int(os.getenv('AI_INIT_RETRY_SECONDS', '300'))
        with _ai_engine_lock:
            _ai_engine = None
            _ai_engine_init_error = str(e)
            _ai_engine_next_retry_at = now + datetime.timedelta(seconds=retry_seconds)
        logger.exception("❌ Failed to initialize AI engine (will continue without AI)")
    finally:
        with _ai_engine_lock:
            _ai_engine_init_in_progress = False


def get_ai_engine():
    """Lazily initialize and cache the AI engine.

    This prevents the whole API server from failing to start when the model
    download is slow or blocked.
    """
    global _ai_engine, _ai_engine_init_error, _ai_engine_next_retry_at, _ai_engine_init_in_progress

    if os.getenv('DISABLE_AI', '0') == '1':
        return None

    now = datetime.datetime.utcnow()
    with _ai_engine_lock:
        if _ai_engine is not None:
            return _ai_engine

        # If initialization previously failed, avoid retrying on every request.
        if _ai_engine_next_retry_at is not None and now < _ai_engine_next_retry_at:
            return None

        # If already initializing in the background, don't block.
        if _ai_engine_init_in_progress:
            return None

        # Start background initialization and return immediately.
        _ai_engine_init_in_progress = True

    threading.Thread(target=_init_ai_engine_worker, daemon=True).start()
    return None


def _get_student_skills_for_matching(student: User):
    skills = list(student.skills or [])
    verified = VerifiedSkill.query.filter_by(student_id=student.id, is_verified=True).all()
    skills.extend([v.skill for v in verified if v.skill])
    return skills


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
            user_role = (getattr(current_user, 'role', '') or '').lower().strip()
            allowed_roles = {(r or '').lower().strip() for r in roles}
            if user_role not in allowed_roles:
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
            # Accept both legacy `mssv` and canonical `student_id`.
            incoming_student_id = (data.get('student_id') or data.get('mssv') or '').strip()
            user.student_id = incoming_student_id or None
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
            logger.info(f"   Email: {saved_user.email}")
            logger.info(f"   Role: {saved_user.role}")
            #logger.info(f"   Created at: {saved_user.created_at}")
            #created_time = getattr(saved_user, 'created_at', 'N/A')
            #logger.info(f"   Created at: {created_time}")
            logger.info(f"   Created at: {getattr(saved_user, 'created_at', 'N/A')}")
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
        data = request.get_json()
        
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'message': 'Vui lòng nhập đầy đủ email và mật khẩu'}), 400

        email = data.get('email', '').lower().strip()
        password = data.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            logger.warning(f"❌ Đăng nhập thất bại: {email}")
            return jsonify({'message': 'Email hoặc mật khẩu không chính xác'}), 401
        
        if not getattr(user, 'is_active', True):
            return jsonify({'message': 'Tài khoản đã bị vô hiệu hóa'}), 403
        
        # Generate token
        token_payload = {
            'user_id': str(user.id),
            'email': user.email,
            'role': user.role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }
        token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')
        
        logger.info(f"✅ User {email} đăng nhập thành công!")
        
        return jsonify({
            'message': 'Đăng nhập thành công',
            'token': token,
            'access_token': token,
            'token_type': 'bearer',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"🔴 Lỗi nghiêm trọng tại /login: {str(e)}")
        return jsonify({'message': 'Lỗi hệ thống', 'error': str(e)}), 500

@app.route('/api/admin/bootstrap', methods=['POST'])
def bootstrap_admin():
    """Create or promote an admin user with a shared bootstrap key."""
    bootstrap_key = os.getenv('BOOTSTRAP_ADMIN_KEY')
    if not bootstrap_key:
        return jsonify({'message': 'Bootstrap is disabled'}), 403

    provided_key = request.headers.get('X-Bootstrap-Key', '')
    if provided_key != bootstrap_key:
        return jsonify({'message': 'Invalid bootstrap key'}), 403

    data = request.json or {}
    email = (data.get('email', '') or '').lower().strip()
    full_name = data.get('full_name') or 'Admin'
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Missing email or password'}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        user.role = 'admin'
        user.full_name = full_name or user.full_name
        user.set_password(password)
    else:
        user = User(email=email, full_name=full_name, role='admin')
        user.set_password(password)
        db.session.add(user)

    db.session.commit()
    return jsonify({'message': 'Admin ready', 'user': user.to_dict()}), 200

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

        # Normalize key names so the frontend can rely on a stable shape.
        # (Some older clients used `mssv` instead of `student_id`.)
        if not profile.get('name') and profile.get('full_name'):
            profile['name'] = profile.get('full_name')
        if not profile.get('full_name') and profile.get('name'):
            profile['full_name'] = profile.get('name')
        if not profile.get('student_id') and profile.get('mssv'):
            profile['student_id'] = profile.get('mssv')
        if not profile.get('mssv') and profile.get('student_id'):
            profile['mssv'] = profile.get('student_id')
        profile.setdefault('email', '')
        profile.setdefault('phone', '')
        profile.setdefault('gpa', 0.0)
        
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

@app.route('/api/student/applications/<application_id>', methods=['DELETE'])
@token_required
@role_required(['student'])
def withdraw_student_application(current_user, application_id):
    try:
        application = Application.query.get(application_id)
        if not application or application.student_id != current_user.id:
            return jsonify({'message': 'Application not found'}), 404

        application.status = 'withdrawn'
        db.session.commit()

        return jsonify({'message': 'Application withdrawn'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/student/profile', methods=['PUT'])
@token_required
@role_required(['student'])
def update_student_profile(current_user):
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            return jsonify({'message': 'Invalid JSON body'}), 400

        # Normalize common payload shapes from the frontend.
        # These columns are ARRAY(String) in Postgres; ensure we persist lists.
        if 'skills' in data and isinstance(data.get('skills'), str):
            data['skills'] = [s.strip() for s in data['skills'].split(',') if s.strip()]
        if 'research_interests' in data and isinstance(data.get('research_interests'), str):
            data['research_interests'] = [s.strip() for s in data['research_interests'].split(',') if s.strip()]
        
        # Update basic info
        if 'name' in data or 'full_name' in data:
            current_user.full_name = (data.get('full_name') or data.get('name') or current_user.full_name)

        # Student identifiers
        if 'student_id' in data or 'mssv' in data:
            incoming_student_id = (data.get('student_id') or data.get('mssv') or '').strip()
            current_user.student_id = incoming_student_id or None

        if 'faculty' in data:
            current_user.faculty = data.get('faculty')
        if 'phone' in data:
            current_user.phone = data.get('phone')
        if 'gpa' in data:
            try:
                current_user.gpa = float(data.get('gpa'))
            except (TypeError, ValueError):
                pass
        if 'year_of_study' in data:
            try:
                current_user.year_of_study = int(data.get('year_of_study'))
            except (TypeError, ValueError):
                pass
        
        # Update skills and research interests
        if (
            'skills' in data
            or 'research_interests' in data
            or 'faculty' in data
            or 'department' in data
            or 'research_fields' in data
        ):
            # Update skill vector for AI matching using combined text
            combined_parts = []
            updated_skills = data.get('skills', current_user.skills or [])
            updated_interests = data.get('research_interests', current_user.research_interests or [])

            if updated_skills:
                combined_parts.append(' '.join(updated_skills) if isinstance(updated_skills, list) else str(updated_skills))
            if updated_interests:
                combined_parts.append(' '.join(updated_interests) if isinstance(updated_interests, list) else str(updated_interests))
            if current_user.faculty:
                combined_parts.append(str(current_user.faculty))
            if current_user.department:
                combined_parts.append(str(current_user.department))
            if current_user.research_fields:
                combined_parts.append(' '.join(current_user.research_fields))

            if combined_parts:
                ai_engine = get_ai_engine()
                if ai_engine is not None:
                    current_user.skill_vector = ai_engine.get_embedding(' '.join(combined_parts))
        
        if 'skills' in data:
            current_user.skills = data['skills']
        
        if 'research_interests' in data:
            current_user.research_interests = data['research_interests']
        
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            error_msg = str(e.orig) if getattr(e, 'orig', None) else str(e)
            if 'student_id' in error_msg.lower() or 'unique' in error_msg.lower():
                return jsonify({'message': 'MSSV đã tồn tại (student_id must be unique)'}), 409
            return jsonify({'message': 'Integrity error', 'error': error_msg}), 409

        # Invalidate AI cache so match scores reflect updated profile immediately.
        # Without this, SmartMatchAIService may return stale cached results.
        try:
            ai_engine = get_ai_engine()
            if ai_engine is not None:
                removed = ai_engine.invalidate_student_match_cache(current_user.id)
                app.logger.info(f"🧹 Invalidated {removed} match-cache entries for student {current_user.email}")
        except Exception:
            # Non-fatal: cache invalidation should not block profile updates.
            app.logger.exception("Failed to invalidate AI match cache")
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': current_user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/student/apply', methods=['POST'])
@token_required
@role_required(['student'])
def apply_student_api(current_user):
    data = request.json or {}
    project_id = data.get('project_id')
    if not project_id:
        return jsonify({'message': 'Missing project_id'}), 400
    return _apply_to_project_impl(current_user, project_id)


@app.route('/api/applications', methods=['POST'])
@token_required
@role_required(['student'])
def create_application(current_user):
    """Create an application (student applies to a project)."""
    data = request.json or {}
    project_id = data.get('project_id')
    if not project_id:
        return jsonify({'message': 'Missing project_id'}), 400
    return _apply_to_project_impl(current_user, project_id)


def _apply_to_project_impl(current_user, project_id):
    """Shared implementation for applying to a project.

    IMPORTANT: This is intentionally NOT decorated as a route.
    """
    try:
        # 1. Tìm dự án
        project = Project.query.options(joinedload(getattr(Project, 'lecturer'))).get(project_id)
        if not project:
            return jsonify({'message': 'Project not found'}), 404

        if project.status != 'open':
            return jsonify({'message': 'Project is not accepting applications'}), 400

        # 2. Kiểm tra trùng lặp đơn ứng tuyển
        existing_application = Application.query.filter_by(
            student_id=current_user.id,
            project_id=project.id
        ).first()

        if existing_application:
            return jsonify({'message': 'Already applied to this project'}), 400

        # Kick off AI initialization in the background; allow applying even if AI isn't ready yet.
        ai_engine = get_ai_engine()
        if ai_engine is None:
            student_skills = _get_student_skills_for_matching(current_user)
            project_skills = (project.required_skills or []) + (project.preferred_skills or [])
            score = calculate_match_score(student_skills, project_skills)
            match_result = {
                "match_score": score,
                "match_level": "basic",
                "match_details": {"score": score, "reason": "Fallback skill overlap score (AI not ready)"},
                "recommendation": "AI đang khởi động"
            }
        else:
            match_result = ai_engine.calculate_comprehensive_match_score(current_user, project)
            score = match_result.get("match_score", 0.0)

        # 4. Lấy nội dung đơn ứng tuyển từ request
        application_text = ''
        if request.json and isinstance(request.json, dict):
            application_text = request.json.get('application_text', '')

        # 5. Khởi tạo và lưu đơn ứng tuyển
        application = Application(
            student_id=current_user.id,
            project_id=project.id,
            match_score=score,
            match_details=match_result,
            application_text=application_text,
            status='pending'
        )

        db.session.add(application)
        db.session.commit()

        # Trả về kết quả đồng nhất với database
        return jsonify({
            'message': 'Ứng tuyển thành công!',
            'match_score': match_result.get('match_score', score),
            'match_level': match_result.get('match_level'),
            'reason': (match_result.get('match_details') or {}).get('reason')
        }), 201

    except Exception as e:
        db.session.rollback()
        app.logger.exception('Error applying to project')
        return jsonify({'message': 'Lỗi hệ thống khi ứng tuyển', 'error': str(e)}), 500

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
        app.logger.info(f"🔍 Đang tìm dự án phù hợp cho: {current_user.email}")

        # Lấy các dự án đang mở
        projects = (
            Project.query
            .options(joinedload(getattr(Project, 'lecturer')))
            .filter_by(status='open', is_public=True)
            .all()
        )

        student_skills = _get_student_skills_for_matching(current_user)

        # Kick off AI initialization in the background (non-blocking).
        ai_engine = get_ai_engine()
        ai_ready = ai_engine is not None

        recommendations = []
        for project in projects:
            project_skills = (project.required_skills or []) + (project.preferred_skills or [])

            if ai_ready:
                match_result = ai_engine.calculate_comprehensive_match_score(current_user, project)
                score = match_result.get("match_score", 0.0)
                explanation = match_result.get("recommendation")
                match_details = match_result.get("match_details")
            else:
                score = calculate_match_score(student_skills, project_skills)
                explanation = "AI đang khởi động, dùng điểm phù hợp tạm thời theo kỹ năng"
                match_details = {
                    "score": score,
                    "reason": "Fallback skill overlap score (AI not ready)"
                }
            
            project_data = project.to_dict()
            project_data['score'] = score  # Backward-compatible
            project_data['match_score'] = score
            project_data['explanation'] = explanation
            
            # Kiểm tra trạng thái ứng tuyển
            application = Application.query.filter_by(student_id=current_user.id, project_id=project.id).first()
            project_data['has_applied'] = bool(application)
            project_data['application_status'] = application.status if application else None
            
            project_data['match_details'] = match_details
            recommendations.append(project_data)

        # Sắp xếp theo điểm số giảm dần
        recommendations.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return jsonify({
            'recommendations': recommendations,
            'count': len(recommendations),
            'ai_ready': ai_ready
        })

    except Exception as e:
        app.logger.exception('❌ Lỗi tại /api/student/projects/recommended')
        return jsonify({'message': str(e)}), 500

@app.route('/api/student/projects/<project_id>/apply', methods=['POST'])
@token_required
@role_required(['student'])
def apply_to_project(current_user, project_id):
    return _apply_to_project_impl(current_user, project_id)

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
        
        # Xử lý skills - đảm bảo là list
        required_skills = data.get('required_skills', [])
        if isinstance(required_skills, str):
            required_skills = [s.strip() for s in required_skills.split(',') if s.strip()]
        
        preferred_skills = data.get('preferred_skills', [])
        if isinstance(preferred_skills, str):
            preferred_skills = [s.strip() for s in preferred_skills.split(',') if s.strip()]
        
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
            required_skills=required_skills,  # Đã xử lý
            preferred_skills=preferred_skills,  # Đã xử lý
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
            if isinstance(data['required_skills'], list):
                project_text += ' ' + ' '.join(data['required_skills'])
            else:
                project_text += ' ' + data['required_skills']
        ai_engine = get_ai_engine()
        if ai_engine is not None:
            project.requirement_vector = ai_engine.get_embedding(project_text)
        
        db.session.add(project)
        db.session.commit()
        
        return jsonify({
            'message': 'Project created successfully',
            'project': project.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating project: {e}")
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


@app.route('/api/lecturer/projects/<project_id>', methods=['PUT'])
@token_required
@role_required(['lecturer'])
def update_project(current_user, project_id):
    try:
        project = Project.query.get(project_id)
        if not project or project.lecturer_id != current_user.id:
            return jsonify({'message': 'Không tìm thấy dự án hoặc bạn không có quyền sửa'}), 404
        
        data = request.json or {}
        
        # 1. Cập nhật các thông số cơ bản (Điều chỉnh thông số)
        if 'title' in data: project.title = data['title']
        if 'description' in data: 
            project.description = data['description']
            # Nếu sửa mô tả, phải cập nhật lại Vector AI ngay
            ai_engine = get_ai_engine()
            if ai_engine is not None:
                project.requirement_vector = ai_engine.get_embedding(data['description'])
            
        if 'max_students' in data: project.max_students = data['max_students']
        if 'difficulty_level' in data: project.difficulty_level = data['difficulty_level']
        
        # 2. Cập nhật Tình trạng dự án (Nút Đóng/Mở)
        if 'status' in data: 
            project.status = data['status'] # 'open' hoặc 'closed'
            
        if 'is_public' in data:
            project.is_public = data['is_public'] # Hiện hoặc Ẩn dự án

        db.session.commit()
        return jsonify({
            'message': 'Cập nhật dự án thành công',
            'project': project.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/lecturer/projects/<project_id>/applications', methods=['GET'])
@token_required
@role_required(['lecturer'])
def get_project_applications(current_user, project_id):
    try:
        project = Project.query.get(project_id)
        if not project or project.lecturer_id != current_user.id:
            return jsonify({'message': 'Project not found or access denied'}), 404
        
        applications = Application.query.filter_by(project_id=project.id)\
                        .order_by(Application.match_score.desc()).all()
        
        applications_data = []
        for app in applications:
            app_data = app.to_dict()
            
            # Get student details
            if app.student:
                app_data['student_profile'] = app.student.to_dict()
            
            applications_data.append(app_data)
        
        return jsonify({
            'project': project.to_dict(),
            'applications': applications_data,
            'count': len(applications_data)
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/lecturer/all-applications', methods=['GET'])
@token_required
@role_required(['lecturer'])
def get_all_lecturer_applications(current_user):
    try:
        # Lấy tất cả đơn của tất cả dự án thuộc giảng viên này
        apps = Application.query.join(Project).filter(Project.lecturer_id == current_user.id).all()
        return jsonify([a.to_dict() for a in apps])
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/lecturer/applications/<application_id>/review', methods=['PUT'])
@token_required
@role_required(['lecturer'])
def review_application(current_user, application_id):
    try:
        data = request.json
        status = data.get('status') # 'accepted' hoặc 'rejected'
        feedback = data.get('feedback_text') # Nhận ghi chú từ Frontend

        if not status:
            return jsonify({'message': 'Thiếu trạng thái (status)'}), 400
        
        application = Application.query.get(application_id)
        if not application:
            return jsonify({'message': 'Không tìm thấy đơn ứng tuyển'}), 404
        
        # 1. Kiểm tra xem Giảng viên có quyền trên dự án này không
        project = Project.query.get(application.project_id)
        if not project or project.lecturer_id != current_user.id:
            return jsonify({'message': 'Bạn không có quyền thực hiện thao tác này'}), 403
        
        # 2. Cập nhật thông tin đơn ứng tuyển
        application.status = status

        #lưu ghi chú phản hồi 
        application.feedback_text = feedback
        application.reviewed_at = datetime.datetime.utcnow()
        #lưu lý do từ chối nếu có 
        if status == 'rejected':
            application.rejection_reason = feedback
        # Bổ sung các trường audit (người duyệt, thời gian duyệt)
        if hasattr(application, 'reviewed_at'):
            application.reviewed_at = datetime.datetime.utcnow()
        
        # 3. LOGIC TỰ ĐỘNG ĐÓNG DỰ ÁN
        # Chỉ chạy kiểm tra này nếu Giảng viên vừa nhấn "Chấp nhận"
        if status == 'accepted':
            # Đếm số lượng sinh viên đã được chấp nhận cho dự án này
            accepted_count = Application.query.filter_by(
                project_id=project.id, 
                status='accepted'
            ).count()
            
            # Nếu số người đã nhận >= số lượng tối đa cho phép
            if accepted_count >= project.max_students:
                project.status = 'closed' # Tự động đóng dự án
                logger.info(f"🚩 Dự án '{project.title}' đã tự động đóng (Đã nhận {accepted_count}/{project.max_students} SV).")
        
        # 4. Lưu tất cả thay đổi vào Database
        db.session.commit()
        
        return jsonify({
            'message': 'Cập nhật đơn ứng tuyển thành công',
            'application': application.to_dict(),
            'project_status': project.status # Trả về để Frontend cập nhật giao diện ngay
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"🔴 Lỗi khi duyệt đơn: {str(e)}")
        return jsonify({'message': 'Lỗi server nội bộ', 'details': str(e)}), 500

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
    projects = (
        Project.query
        .options(joinedload(getattr(Project, 'lecturer')))
        .filter_by(status='open', is_public=True)
        .all()
    )
    return jsonify({'projects': [p.to_dict() for p in projects]})


@app.route('/api/projects', methods=['GET'])
def list_projects_api():
    """List open public projects.

    If a valid student JWT is provided (Authorization: Bearer <token>), include
    a `match_score` computed from the student's skills.
    """
    try:
        current_user = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
            try:
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                current_user = User.query.get(data.get('user_id'))
            except Exception:
                current_user = None

        student_skills = []
        if current_user and (getattr(current_user, 'role', '') or '').lower() == 'student':
            student_skills = _get_student_skills_for_matching(current_user)

        projects = (
            Project.query
            .options(joinedload(getattr(Project, 'lecturer')))
            .filter_by(status='open', is_public=True)
            .all()
        )

        items = []
        for project in projects:
            project_data = project.to_dict()
            project_skills = (project.required_skills or []) + (project.preferred_skills or [])
            score = calculate_match_score(student_skills, project_skills) if student_skills else 0.0
            project_data['score'] = score  # Backward-compatible
            project_data['match_score'] = score
            items.append(project_data)

        return jsonify({'projects': items, 'count': len(items)})
    except Exception as e:
        app.logger.exception('❌ Lỗi tại /api/projects')
        return jsonify({'message': str(e)}), 500

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project_detail(project_id):
    try:
        project = Project.query.options(joinedload(getattr(Project, 'lecturer'))).get(project_id)
        if not project:
            return jsonify({'message': 'Project not found'}), 404

        current_user = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
            try:
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                current_user = User.query.get(data.get('user_id'))
            except Exception:
                current_user = None

        project_data = project.to_dict()
        if current_user and (getattr(current_user, 'role', '') or '').lower() == 'student':
            student_skills = _get_student_skills_for_matching(current_user)
            project_skills = (project.required_skills or []) + (project.preferred_skills or [])
            score = calculate_match_score(student_skills, project_skills) if student_skills else 0.0
            project_data['score'] = score
            project_data['match_score'] = score

        return jsonify(project_data)
    except Exception as e:
        return jsonify({'message': str(e)}), 500

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

@app.route('/api/admin/stats', methods=['GET'])
@token_required
@role_required(['admin'])
def admin_get_stats(current_user):
    try:
        total_students = User.query.filter_by(role='student').count()
        total_lecturers = User.query.filter_by(role='lecturer').count()
        total_projects = Project.query.count()
        total_applications = Application.query.count()

        applications_with_match = Application.query.filter(Application.match_score > 0).all()
        avg_match_score = np.mean([app.match_score for app in applications_with_match]) if applications_with_match else 0

        # derive top skills from student profiles
        all_skills = []
        students = User.query.filter_by(role='student').all()
        for s in students:
            if s.skills:
                all_skills.extend(s.skills if isinstance(s.skills, list) else [str(s.skills)])

        skill_counter = Counter([skill.strip().lower() for skill in all_skills if isinstance(skill, str) and skill.strip()])
        top_skills = [{'skill': skill, 'count': count} for skill, count in skill_counter.most_common(5)]

        # basic activity list (recent registrations + applications)
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        recent_apps = Application.query.order_by(Application.applied_at.desc()).limit(5).all()
        recent_activities = [
            {
                'type': 'student_register' if u.role == 'student' else 'lecturer_register',
                'message': f"{u.full_name} đăng ký tài khoản",
                'time': u.created_at.isoformat() if u.created_at else None
            }
            for u in recent_users
        ] + [
            {
                'type': 'application',
                'message': f"{a.student.full_name if a.student else 'Sinh viên'} nộp đơn",
                'status': a.status,
                'time': a.applied_at.isoformat() if a.applied_at else None
            }
            for a in recent_apps
        ]

        return jsonify({
            'total_students': total_students,
            'total_lecturers': total_lecturers,
            'total_projects': total_projects,
            'total_applications': total_applications,
            'avg_match_score': round(float(avg_match_score), 2),
            'applications_trend': [],
            'recent_activities': recent_activities,
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
    # IMPORTANT: health checks must be fast and must not trigger heavy work
    # like downloading/initializing the embedding model.
    ai_engine = _ai_engine
    return jsonify({
        'status': 'healthy',
        'service': 'SMART-MATCH AI Backend',
        'version': '2.0.0',
        'ai_enabled': os.getenv('DISABLE_AI', '0') != '1',
        'ai_ready': ai_engine is not None,
        'ai_initializing': _ai_engine_init_in_progress,
        'ai_model': getattr(getattr(ai_engine, 'config', None), 'MODEL_NAME', None)
        or os.getenv('MODEL_NAME')
        or 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
        'ai_error': _ai_engine_init_error,
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

        # Do NOT eagerly initialize the AI engine by default.
        # The model download can be slow/blocked and would delay server startup.
        if os.getenv('INIT_AI_ON_STARTUP', '0') == '1':
            logger.info("⏳ Initializing AI engine...")
            ai_engine = get_ai_engine()
            if ai_engine is None:
                logger.warning("⚠️ AI engine not ready (server will run without AI for now)")
            else:
                logger.info("✅ AI engine ready")
        else:
            logger.info("⏭️ Skipping AI initialization on startup (lazy-load enabled)")
        
        logger.info("=" * 80)
        logger.info("🟢 BACKEND INITIALIZED SUCCESSFULLY")
        logger.info("=" * 80)

    logger.info("🚀 SMART-MATCH AI BACKEND is running on http://0.0.0.0:5000")

    app.run(host='0.0.0.0', port=5000)