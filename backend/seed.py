import argparse
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from app import app, db, User, Project, get_ai_engine
from seed_data import students, lecturers, projects

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
    student_rows = []
    for s_data in students:
        skill_text = " ".join(
            (s_data.get("skills") or [])
            + (s_data.get("interests") or [])
            + ([s_data.get("major")] if s_data.get("major") else [])
            + ([s_data.get("career_orientation")] if s_data.get("career_orientation") else [])
        )
        vector = _safe_vector(skill_text)
        student_rows.append(
            {
                "email": s_data["email"].lower().strip(),
                "password_hash": generate_password_hash("password123"),
                "full_name": s_data["full_name"],
                "role": "student",
                "student_id": s_data.get("student_id") or str(102000000 + s_data["id"]),
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
    stmt = stmt.on_conflict_do_update(index_elements=[User.__table__.c.email], set_=update_cols)
    session.execute(stmt)
    logger.info("Students seeded: %s", len(student_rows))


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


def seed_database(reset=False):
    with app.app_context():
        try:
            if reset:
                logger.info("Resetting database schema...")
                db.drop_all()
                db.create_all()

            with db.session.begin():
                lecturer_id_map = seed_lecturers(db.session)
                seed_students(db.session)
                fill_missing_student_skills(db.session)
                seed_projects(db.session, lecturer_id_map)

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
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    seed_database(reset=args.reset)