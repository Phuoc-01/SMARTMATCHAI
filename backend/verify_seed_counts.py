"""Quick sanity check for seeded volumes.

Run: python backend/verify_seed_counts.py
This script assumes DATABASE_URL is configured the same way as backend/seed.py.
"""

from __future__ import annotations

from sqlalchemy import func

from app import app, db, User
from models import Application, Project


def _dist_count(query):
    return {k: v for k, v in query}


def main() -> None:
    with app.app_context():
        totals = {
            "lecturers": db.session.query(User).filter(User.role == "lecturer").count(),
            "students": db.session.query(User).filter(User.role == "student").count(),
            "projects": db.session.query(Project).count(),
            "applications": db.session.query(Application).count(),
        }

        # Count applications per project, including projects with 0 applications.
        apps_counts_sub = (
            db.session.query(
                Project.id.label("project_id"),
                func.count(Application.id).label("c"),
            )
            .outerjoin(Application, Application.project_id == Project.id)
            .group_by(Project.id)
            .subquery()
        )
        apps_minmax = db.session.query(func.min(apps_counts_sub.c.c), func.max(apps_counts_sub.c.c)).one()
        apps_dist = (
            db.session.query(apps_counts_sub.c.c, func.count())
            .group_by(apps_counts_sub.c.c)
            .order_by(apps_counts_sub.c.c)
            .all()
        )

        # Count accepted applications per project ("đã tham gia"), including 0.
        accepted_counts_sub = (
            db.session.query(
                Project.id.label("project_id"),
                func.count(Application.id).label("c"),
            )
            .outerjoin(
                Application,
                (Application.project_id == Project.id) & (Application.status == "accepted"),
            )
            .group_by(Project.id)
            .subquery()
        )
        accepted_minmax = db.session.query(
            func.min(accepted_counts_sub.c.c),
            func.max(accepted_counts_sub.c.c),
        ).one()
        accepted_dist = (
            db.session.query(accepted_counts_sub.c.c, func.count())
            .group_by(accepted_counts_sub.c.c)
            .order_by(accepted_counts_sub.c.c)
            .all()
        )

        print("Totals:")
        for k, v in totals.items():
            print(f"- {k}: {v}")

        print("\nApplications per project:")
        print(f"- min/max: {apps_minmax}")
        print(f"- dist: {_dist_count(apps_dist)}")

        print("\nAccepted per project:")
        print(f"- min/max: {accepted_minmax}")
        print(f"- dist: {_dist_count(accepted_dist)}")


if __name__ == "__main__":
    main()
