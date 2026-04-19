import argparse
import logging
from datetime import date, datetime, timedelta

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from app import (
    app,
    db,
    User,
    Project,
    Application,
    ProjectUpdate,
    ProjectMilestone,
    ProjectMilestoneProgress,
    get_ai_engine,
    SkillLibrary,
    Notification,
    Report,
    AuditLog,
)
from seed_data import students, lecturers, projects, skills_library, applications

VECTOR_DIM = 384

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def _safe_vector(text):
    engine = get_ai_engine()
    if engine is not None:
        return engine.get_embedding(text)
    return [0.0] * VECTOR_DIM


def seed_lecturers(session):
    logger.info("Seeding lecturers...")
    lecturer_rows = []
    for l_data in lecturers:
        skill_text = " ".join(
            (l_data.get("skills") or [])
            + (l_data.get("research_fields") or [])
            + (l_data.get("research_interests") or [])
        )
        vector = _safe_vector(skill_text) if skill_text.strip() else [0.0] * VECTOR_DIM
        lecturer_rows.append(
            {
                "email": l_data["email"].lower().strip(),
                "password_hash": generate_password_hash("password123"),
                "full_name": l_data["full_name"],
                "role": "lecturer",
                "phone": l_data.get("phone"),
                "department": l_data.get("department"),
                "research_fields": l_data.get("research_fields", []),
                "position": l_data.get("position") or "Giảng viên",
                "skills": l_data.get("skills", []),
                "research_interests": l_data.get("research_interests", []),
                "skill_vector": vector,
            }
        )

    if not lecturer_rows:
        return {}

    stmt = insert(User.__table__).values(lecturer_rows)
    update_cols = {
        "full_name": stmt.excluded.full_name,
        "role": stmt.excluded.role,
        "phone": stmt.excluded.phone,
        "department": stmt.excluded.department,
        "research_fields": stmt.excluded.research_fields,
        "position": stmt.excluded.position,
        "skills": stmt.excluded.skills,
        "research_interests": stmt.excluded.research_interests,
        "skill_vector": stmt.excluded.skill_vector,
    }
    stmt = stmt.on_conflict_do_update(index_elements=[User.__table__.c.email], set_=update_cols)
    session.execute(stmt)

    lecturer_emails = [row["email"] for row in lecturer_rows]
    saved = session.query(User).filter(User.email.in_(lecturer_emails)).all()
    email_to_id = {user.email: user.id for user in saved}

    lecturer_id_map = {}
    for l_data in lecturers:
        email = l_data["email"].lower().strip()
        if email in email_to_id:
            lecturer_id_map[l_data["id"]] = email_to_id[email]

    logger.info("Lecturers seeded: %s", len(lecturer_id_map))
    return lecturer_id_map


def seed_students(session):
    logger.info("Seeding students...")

    # Soft-purge legacy/test seed accounts (avoid FK violations when apps reference old users).
    # We deactivate them and rewrite emails to unique placeholders so they won't be used for login.
    from sqlalchemy import or_

    legacy_q = (
        session.query(User)
        .filter(User.role == "student")
        .filter(
            or_(
                User.student_id.like("102000%"),
                User.email.ilike("student%@%"),
                User.email.ilike("%test%"),
            )
        )
    )
    legacy_users = legacy_q.all()
    if legacy_users:
        for u in legacy_users:
            u.is_active = False
            # Ensure no UNIQUE(email) collision with new MSSV emails.
            u.email = f"legacy_{u.id.hex[:12]}@invalid.local"
        logger.info("Soft-purged legacy/test student accounts: %s", len(legacy_users))

    student_rows = []
    student_ids = []
    for s_data in students:
        skill_text = " ".join(
            (s_data.get("skills") or [])
            + (s_data.get("interests") or [])
            + ([s_data.get("major")] if s_data.get("major") else [])
            + ([s_data.get("career_orientation")] if s_data.get("career_orientation") else [])
        )
        vector = _safe_vector(skill_text)
        student_id_value = s_data.get("student_id") or str(102000000 + s_data["id"])
        student_ids.append(student_id_value)
        student_rows.append(
            {
                "email": s_data["email"].lower().strip(),
                "password_hash": generate_password_hash("password123"),
                "full_name": s_data["full_name"],
                "role": "student",
                "student_id": student_id_value,
                "faculty": s_data.get("faculty") or s_data.get("major"),
                "phone": s_data.get("phone"),
                "skills": s_data.get("skills", []),
                "research_interests": s_data.get("research_interests") or s_data.get("interests", []),
                "gpa": s_data.get("gpa"),
                "year_of_study": s_data.get("year_of_study") or s_data.get("year"),
                "skill_vector": vector,
            }
        )

    if not student_rows:
        return

    stmt = insert(User.__table__).values(student_rows)
    update_cols = {
        "email": stmt.excluded.email,
        "full_name": stmt.excluded.full_name,
        "role": stmt.excluded.role,
        "student_id": stmt.excluded.student_id,
        "faculty": stmt.excluded.faculty,
        "phone": stmt.excluded.phone,
        "skills": stmt.excluded.skills,
        "research_interests": stmt.excluded.research_interests,
        "gpa": stmt.excluded.gpa,
        "year_of_study": stmt.excluded.year_of_study,
        "skill_vector": stmt.excluded.skill_vector,
    }
    # Students have a UNIQUE(student_id). Use it for idempotent upserts even if
    # email domains change (otherwise we can hit UNIQUE violations).
    stmt = stmt.on_conflict_do_update(index_elements=[User.__table__.c.student_id], set_=update_cols)
    session.execute(stmt)
    logger.info("Students seeded: %s", len(student_rows))

    # Build a mapping from numeric seed_data student IDs -> UUIDs in users table.
    saved = session.query(User).filter(User.student_id.in_(student_ids)).all()
    student_id_to_uuid = {str(user.student_id): user.id for user in saved}
    student_id_map = {}
    for s_data in students:
        sid = str(s_data.get("student_id") or str(102000000 + s_data["id"]))
        if sid in student_id_to_uuid:
            student_id_map[s_data["id"]] = student_id_to_uuid[sid]

    logger.info("Student ID map built: %s", len(student_id_map))
    return student_id_map


def seed_applications_from_seed_data(session, *, student_id_map, lecturer_id_map):
    """Seed student applications defined in seed_data.py.

    Uses numeric IDs from seed_data and resolves them to DB UUIDs.
    Idempotent: updates existing rows for the same (student_id, project_id).
    """
    if not applications:
        return

    project_seed_by_id = {int(p.get('id')): p for p in (projects or []) if p.get('id') is not None}

    # Build a lookup of projects in DB keyed by (lecturer_uuid, title)
    desired_lecturer_ids = set()
    desired_titles = set()
    for p in (projects or []):
        lecturer_uuid = lecturer_id_map.get(p.get('lecturer_id'))
        if lecturer_uuid and p.get('title'):
            desired_lecturer_ids.add(lecturer_uuid)
            desired_titles.add(p['title'])

    if not desired_lecturer_ids or not desired_titles:
        logger.warning('Skipping application seed: no projects resolved')
        return

    db_projects = (
        session.query(Project)
        .filter(Project.lecturer_id.in_(list(desired_lecturer_ids)), Project.title.in_(list(desired_titles)))
        .all()
    )
    project_db_by_key = {(p.lecturer_id, p.title): p for p in db_projects}

    created = 0
    updated = 0
    skipped = 0
    now = datetime.utcnow()

    for idx, a in enumerate(applications, start=1):
        seed_student_id = int(a.get('student_id') or 0)
        seed_project_id = int(a.get('project_id') or 0)
        if not seed_student_id or not seed_project_id:
            skipped += 1
            continue

        student_uuid = student_id_map.get(seed_student_id)
        if not student_uuid:
            logger.warning('Skipping application: student_id %s not found', seed_student_id)
            skipped += 1
            continue

        project_seed = project_seed_by_id.get(seed_project_id)
        if not project_seed:
            logger.warning('Skipping application: project_id %s not found in seed_data', seed_project_id)
            skipped += 1
            continue

        lecturer_uuid = lecturer_id_map.get(project_seed.get('lecturer_id'))
        title = project_seed.get('title')
        if not lecturer_uuid or not title:
            logger.warning('Skipping application: cannot resolve project lecturer/title for project_id %s', seed_project_id)
            skipped += 1
            continue

        project_obj = project_db_by_key.get((lecturer_uuid, title))
        if not project_obj:
            logger.warning('Skipping application: project not found in DB for (%s, %s)', lecturer_uuid, title)
            skipped += 1
            continue

        status = (a.get('status') or 'pending').strip()
        match_score = a.get('match_score')
        application_text = a.get('application_text')
        feedback_text = a.get('feedback_text')
        rejection_reason = a.get('rejection_reason')

        applied_at = a.get('applied_at')
        if applied_at is None:
            applied_at = now - timedelta(hours=idx)

        reviewed_at = a.get('reviewed_at')
        reviewed_by = a.get('reviewed_by')
        if status in ('accepted', 'rejected', 'reviewing', 'shortlisted'):
            reviewed_by = reviewed_by or project_obj.lecturer_id
            reviewed_at = reviewed_at or now - timedelta(hours=max(1, idx // 2))

        existing = (
            session.query(Application)
            .filter(Application.project_id == project_obj.id, Application.student_id == student_uuid)
            .first()
        )
        payload_details = dict(a.get('match_details') or {})
        payload_details.setdefault('seed', True)
        payload_details.setdefault('source', 'seed_data.applications')

        if existing:
            existing.status = status
            if match_score is not None:
                existing.match_score = match_score
            existing.match_details = payload_details
            existing.application_text = application_text
            existing.feedback_text = feedback_text
            existing.rejection_reason = rejection_reason
            existing.applied_at = applied_at
            existing.reviewed_at = reviewed_at
            existing.reviewed_by = reviewed_by
            updated += 1
        else:
            session.add(
                Application(
                    student_id=student_uuid,
                    project_id=project_obj.id,
                    match_score=match_score if match_score is not None else 0,
                    match_details=payload_details,
                    status=status,
                    application_text=application_text,
                    feedback_text=feedback_text,
                    rejection_reason=rejection_reason,
                    applied_at=applied_at,
                    reviewed_at=reviewed_at,
                    reviewed_by=reviewed_by,
                )
            )
            created += 1

    logger.info(
        'Seed_data applications processed: %s created, %s updated, %s skipped',
        created,
        updated,
        skipped,
    )


def fill_missing_student_skills(session):
    """Assign default skills to any student accounts missing skills.

    This helps dev/test accounts receive non-zero match scores when AI is not ready.
    """
    default_skills = ["Python", "SQL", "Docker"]
    students = session.query(User).filter_by(role="student").all()
    updated = 0
    for student in students:
        if not (student.skills or []):
            student.skills = list(default_skills)
            student.skill_vector = _safe_vector(" ".join(default_skills))
            updated += 1
    if updated:
        logger.info("Filled missing student skills: %s", updated)


def seed_projects(session, lecturer_id_map):
    logger.info("Seeding projects...")
    if not projects:
        return

    desired = []
    for p_data in projects:
        lecturer_uuid = lecturer_id_map.get(p_data["lecturer_id"])
        if not lecturer_uuid:
            logger.warning(
                "Skipping project '%s' because lecturer_id %s was not found",
                p_data.get("title"),
                p_data.get("lecturer_id"),
            )
            continue

        proj_text = f"{p_data['title']} {p_data['description']}"
        desired.append(
            {
                "title": p_data["title"],
                "description": p_data["description"],
                "research_field": p_data.get("field"),
                "required_skills": p_data.get("required_skills", []),
                "max_students": p_data.get("max_students", 1),
                "lecturer_id": lecturer_uuid,
                "requirement_vector": _safe_vector(proj_text),
                "status": "open",
            }
        )

    if not desired:
        return

    lecturer_ids = list({row["lecturer_id"] for row in desired})
    titles = list({row["title"] for row in desired})
    existing = (
        session.query(Project)
        .filter(Project.lecturer_id.in_(lecturer_ids), Project.title.in_(titles))
        .all()
    )
    existing_map = {(p.lecturer_id, p.title): p for p in existing}

    inserts = []
    updates = 0
    for row in desired:
        key = (row["lecturer_id"], row["title"])
        if key in existing_map:
            project = existing_map[key]
            project.description = row["description"]
            project.research_field = row["research_field"]
            project.required_skills = row["required_skills"]
            project.max_students = row["max_students"]
            project.requirement_vector = row["requirement_vector"]
            project.status = row["status"]
            updates += 1
        else:
            inserts.append(Project(**row))

    if inserts:
        session.bulk_save_objects(inserts)

    logger.info("Projects seeded: %s inserts, %s updates", len(inserts), updates)


def seed_skills_library(session):
    """Seed the global skills library (idempotent upsert by name)."""
    if not skills_library:
        return

    rows = []
    for item in skills_library:
        name = (item.get('name') or '').strip()
        if not name:
            continue
        rows.append(
            {
                'name': name,
                'category': (item.get('category') or None),
                'description': (item.get('description') or None),
                'related_skills': (item.get('related_skills') or []),
                'popularity_score': int(item.get('popularity_score') or 0),
            }
        )

    if not rows:
        return

    stmt = insert(SkillLibrary.__table__).values(rows)
    update_cols = {
        'category': stmt.excluded.category,
        'description': stmt.excluded.description,
        'related_skills': stmt.excluded.related_skills,
        'popularity_score': stmt.excluded.popularity_score,
        'updated_at': datetime.utcnow(),
    }
    stmt = stmt.on_conflict_do_update(index_elements=[SkillLibrary.__table__.c.name], set_=update_cols)
    session.execute(stmt)
    logger.info('Skills library upserted: %s items', len(rows))


def _ensure_notification(session, *, user_id, type, title, message, data=None, priority='normal'):
    exists = (
        session.query(Notification)
        .filter(Notification.user_id == user_id, Notification.type == type, Notification.title == title)
        .first()
    )
    if exists:
        return False
    session.add(
        Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            data=data or {},
            priority=priority,
        )
    )
    return True


def seed_demo_notifications_reports(session):
    """Create a small set of demo notifications/reports/audit logs for UI testing."""
    users = session.query(User).order_by(User.created_at.asc()).limit(20).all()
    if not users:
        return

    created_notifications = 0
    for u in users[:12]:
        created = _ensure_notification(
            session,
            user_id=u.id,
            type='welcome',
            title='Chào mừng đến SMART-MATCH AI',
            message='Tài khoản của bạn đã sẵn sàng. Hãy hoàn thiện hồ sơ để nhận gợi ý dự án phù hợp.',
            data={'role': u.role},
        )
        created_notifications += 1 if created else 0

    # Create 2 demo reports (idempotent)
    if len(users) >= 3:
        reporter = users[0]
        reported = users[1]
        exists = (
            session.query(Report)
            .filter(
                Report.reporter_id == reporter.id,
                Report.reported_user_id == reported.id,
                Report.reason == 'Spam/Không phù hợp',
            )
            .first()
        )
        if not exists:
            session.add(
                Report(
                    reporter_id=reporter.id,
                    reported_user_id=reported.id,
                    reason='Spam/Không phù hợp',
                    content='Nội dung/ứng xử không phù hợp với môi trường học thuật.',
                    status='pending',
                )
            )

        reporter2 = users[2]
        exists2 = (
            session.query(Report)
            .filter(
                Report.reporter_id == reporter2.id,
                Report.reported_user_id == reported.id,
                Report.reason == 'Hồ sơ sai thông tin',
            )
            .first()
        )
        if not exists2:
            session.add(
                Report(
                    reporter_id=reporter2.id,
                    reported_user_id=reported.id,
                    reason='Hồ sơ sai thông tin',
                    content='Một số thông tin trong hồ sơ có vẻ không chính xác.',
                    status='pending',
                )
            )

    # Create a few audit logs if table is empty
    if session.query(AuditLog).count() == 0:
        actor = users[0]
        session.add(
            AuditLog(
                user_id=actor.id,
                user_role=actor.role,
                action='seed.demo',
                entity_type='system',
                entity_name='seed.py',
                new_values={'notes': 'Demo audit log created by seed'},
                severity='info',
                request_method='SEED',
                request_url='/seed',
            )
        )

    logger.info('Demo notifications created: %s', created_notifications)


def seed_demo_project_management(session):
    """Seed demo project updates + milestones + (optional) checklist progress.

    Idempotent: safe to run multiple times without duplicating rows.
    """
    projects = (
        session.query(Project)
        .order_by(Project.created_at.asc())
        .limit(10)
        .all()
    )
    if not projects:
        return

    students = (
        session.query(User)
        .filter(User.role == 'student')
        .order_by(User.created_at.asc())
        .limit(50)
        .all()
    )

    today = date.today()
    created_updates = 0
    created_milestones = 0
    created_progress = 0

    for project in projects:
        lecturer_id = project.lecturer_id

        update_payloads = [
            f"Kickoff: Dự án '{project.title}' đã bắt đầu. Các bạn sinh viên hãy chuẩn bị tài liệu và setup môi trường.",
            "Nhắc nhẹ: cập nhật tiến độ hàng tuần và đánh dấu checklist milestones nhé.",
        ]
        for content in update_payloads:
            exists = (
                session.query(ProjectUpdate)
                .filter(ProjectUpdate.project_id == project.id, ProjectUpdate.content == content)
                .first()
            )
            if not exists:
                session.add(
                    ProjectUpdate(
                        project_id=project.id,
                        lecturer_id=lecturer_id,
                        content=content,
                    )
                )
                created_updates += 1

        milestone_payloads = [
            {
                'title': 'Tuần 1: Setup & đọc tài liệu',
                'description': 'Setup môi trường, đọc paper/tài liệu liên quan, chốt scope.',
                'due_date': today + timedelta(days=7),
            },
            {
                'title': 'Tuần 2: Prototype',
                'description': 'Làm prototype nhỏ để validate hướng đi.',
                'due_date': today + timedelta(days=14),
            },
            {
                'title': 'Tuần 3: Báo cáo tiến độ',
                'description': 'Viết báo cáo ngắn + demo kết quả hiện tại.',
                'due_date': today + timedelta(days=21),
            },
        ]

        saved_milestones = []
        for m in milestone_payloads:
            exists = (
                session.query(ProjectMilestone)
                .filter(ProjectMilestone.project_id == project.id, ProjectMilestone.title == m['title'])
                .first()
            )
            if exists:
                saved_milestones.append(exists)
                continue
            milestone = ProjectMilestone(
                project_id=project.id,
                title=m['title'],
                description=m['description'],
                due_date=m['due_date'],
            )
            session.add(milestone)
            saved_milestones.append(milestone)
            created_milestones += 1

        # Flush so milestones get IDs before creating progress
        session.flush()

        # Ensure each project has at least 1 accepted member so the lecturer UI can
        # demonstrate members/evaluation/checklist regardless of pending/rejected apps.
        accepted_count = (
            session.query(Application)
            .filter(Application.project_id == project.id, Application.status == 'accepted')
            .count()
        )
        if accepted_count == 0 and students:
            for student in students:
                exists_app = (
                    session.query(Application)
                    .filter(Application.project_id == project.id, Application.student_id == student.id)
                    .first()
                )
                if exists_app:
                    continue

                session.add(
                    Application(
                        student_id=student.id,
                        project_id=project.id,
                        match_score=85,
                        match_details={'seed': True, 'note': 'Demo accepted application'},
                        status='accepted',
                        application_text='Em xin tham gia dự án và cam kết cập nhật tiến độ đều đặn.',
                        applied_at=datetime.utcnow(),
                        reviewed_at=datetime.utcnow(),
                        reviewed_by=project.lecturer_id,
                    )
                )
                session.flush()
                break

        accepted_apps = (
            session.query(Application)
            .filter(Application.project_id == project.id, Application.status == 'accepted')
            .limit(10)
            .all()
        )
        if not accepted_apps or not saved_milestones:
            continue

        progress_rows = []
        for app_row in accepted_apps:
            for idx, milestone in enumerate(saved_milestones):
                # Make the first milestone done for the first accepted student (nice UI demo)
                is_done = bool(idx == 0 and app_row == accepted_apps[0])
                progress_rows.append(
                    {
                        'milestone_id': milestone.id,
                        'student_id': app_row.student_id,
                        'is_done': is_done,
                        'completed_at': datetime.utcnow() if is_done else None,
                    }
                )

        stmt = insert(ProjectMilestoneProgress.__table__).values(progress_rows)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=[
                ProjectMilestoneProgress.__table__.c.milestone_id,
                ProjectMilestoneProgress.__table__.c.student_id,
            ]
        )
        result = session.execute(stmt)
        try:
            created_progress += int(result.rowcount or 0)
        except Exception:
            # rowcount can be None depending on driver/version
            pass

    logger.info(
        'Demo project management seeded: %s updates, %s milestones, %s progress rows',
        created_updates,
        created_milestones,
        created_progress,
    )


def seed_demo_applications(session):
    """Create demo applications for UI testing (pending + rejected with reasons).

    Idempotent: will not create duplicate applications for the same (project, student).
    """
    projects = (
        session.query(Project)
        .order_by(Project.created_at.asc())
        .limit(10)
        .all()
    )
    if not projects:
        return

    students = (
        session.query(User)
        .filter(User.role == 'student')
        .order_by(User.created_at.asc())
        .limit(50)
        .all()
    )
    if not students:
        return

    created_pending = 0
    created_rejected = 0

    for project in projects:
        # Ensure at least 1 pending application
        pending_exists = (
            session.query(Application)
            .filter(Application.project_id == project.id, Application.status == 'pending')
            .first()
        )
        if not pending_exists:
            for student in students:
                exists_app = (
                    session.query(Application)
                    .filter(Application.project_id == project.id, Application.student_id == student.id)
                    .first()
                )
                if exists_app:
                    continue
                session.add(
                    Application(
                        student_id=student.id,
                        project_id=project.id,
                        match_score=78,
                        match_details={'seed': True, 'note': 'Demo pending application'},
                        status='pending',
                        application_text='Em xin ứng tuyển dự án và mong được thầy/cô xem xét.',
                        applied_at=datetime.utcnow(),
                    )
                )
                session.flush()
                created_pending += 1
                break

        # Ensure at least 1 rejected application with a reason
        rejected_exists = (
            session.query(Application)
            .filter(Application.project_id == project.id, Application.status == 'rejected')
            .first()
        )
        if not rejected_exists:
            for student in students:
                exists_app = (
                    session.query(Application)
                    .filter(Application.project_id == project.id, Application.student_id == student.id)
                    .first()
                )
                if exists_app:
                    continue
                reason = 'Hiện tại hồ sơ/chuyên môn chưa phù hợp yêu cầu dự án. Bạn vui lòng bổ sung kỹ năng và ứng tuyển lại sau.'
                session.add(
                    Application(
                        student_id=student.id,
                        project_id=project.id,
                        match_score=42,
                        match_details={'seed': True, 'note': 'Demo rejected application'},
                        status='rejected',
                        application_text='Em xin ứng tuyển dự án và mong được hướng dẫn thêm.',
                        feedback_text=reason,
                        rejection_reason=reason,
                        applied_at=datetime.utcnow() - timedelta(days=2),
                        reviewed_at=datetime.utcnow() - timedelta(days=1),
                        reviewed_by=project.lecturer_id,
                    )
                )
                session.flush()
                created_rejected += 1
                break

    logger.info(
        'Demo applications seeded: %s pending, %s rejected',
        created_pending,
        created_rejected,
    )


def seed_database(reset=False, extras=True):
    with app.app_context():
        try:
            if reset:
                logger.info("Resetting database schema...")
                db.drop_all()
                db.create_all()

            with db.session.begin():
                lecturer_id_map = seed_lecturers(db.session)
                student_id_map = seed_students(db.session)
                fill_missing_student_skills(db.session)
                seed_projects(db.session, lecturer_id_map)
                seed_applications_from_seed_data(
                    db.session,
                    student_id_map=student_id_map or {},
                    lecturer_id_map=lecturer_id_map or {},
                )
                if extras:
                    seed_skills_library(db.session)
                    seed_demo_notifications_reports(db.session)
                    # If seed_data already defines applications, don't add extra demo
                    # rows that would inflate per-project applicant counts.
                    if not applications:
                        seed_demo_applications(db.session)
                    seed_demo_project_management(db.session)

            logger.info("Seed completed successfully")
        except SQLAlchemyError as exc:
            logger.error("Database error during seed: %s", exc)
            db.session.rollback()
            raise
        except Exception as exc:
            logger.error("Unexpected error during seed: %s", exc)
            db.session.rollback()
            raise


def parse_args():
    parser = argparse.ArgumentParser(description="Seed Smart Match AI database")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate tables before seeding")
    parser.add_argument(
        "--no-extras",
        action="store_true",
        help="Do not seed skills_library and demo notifications/reports",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    seed_database(reset=args.reset, extras=not args.no_extras)