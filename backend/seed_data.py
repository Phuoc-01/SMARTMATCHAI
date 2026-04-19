"""Seed fixtures for Smart Match AI.

This module intentionally contains *data only* (lists of dicts) that are
consumed by `backend/seed.py`.

We keep the author-friendly fields (e.g. `major`, `year`, `interests`) and
also normalize them into the fields used by the unified `users` table
(`student_id`, `faculty`, `year_of_study`, `phone`, `position`, ...).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


_STUDENT_EMAIL_DOMAIN = "sv1.dut.udn.vn"
_LECTURER_EMAIL_DOMAIN = "dut.udn.vn"


def _with_email_domain(email: str, *, domain: str) -> str:
    raw = (email or "").strip().lower()
    if not raw:
        return raw
    local = raw.split("@", 1)[0].strip()
    return f"{local}@{domain}"


def _vn_phone_for(seed_id: int) -> str:
    # Deterministic, valid-looking Vietnamese phone number (10 digits).
    # Example: 09 1234 5678
    return f"09{(10000000 + seed_id):08d}"


def _student_mssv_prefix_for_year(year_of_study: int) -> str:
    year = int(year_of_study or 1)
    mapping = {
        1: "10225",
        2: "10224",
        3: "10223",
        4: "10222",
    }
    return mapping.get(year, "10225")


def _student_mssv_for(*, year_of_study: int, ordinal_in_cohort: int) -> str:
    prefix = _student_mssv_prefix_for_year(year_of_study)
    ordinal = int(ordinal_in_cohort or 1)
    return f"{prefix}{ordinal:04d}"


def _lecturer_position_from_name(full_name: str) -> str:
    # Extract common academic prefixes used in Vietnamese universities.
    match = re.match(r"^(PGS\.TS\.|GS\.TS\.|TS\.|ThS\.)\s+", (full_name or "").strip())
    if match:
        return match.group(1)
    return "Giảng viên"


def _normalize_students(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    year_to_students: Dict[int, List[Dict[str, Any]]] = {}
    for s in raw:
        year_val = s.get("year_of_study")
        if year_val is None:
            year_val = s.get("year")
        try:
            year = int(year_val or 1)
        except (TypeError, ValueError):
            year = 1
        year_to_students.setdefault(year, []).append(s)

    for year, cohort in year_to_students.items():
        cohort_sorted = sorted(cohort, key=lambda x: int(x.get("id") or 0))
        for ordinal, s in enumerate(cohort_sorted, start=1):
            mssv = _student_mssv_for(year_of_study=year, ordinal_in_cohort=ordinal)
            s["student_id"] = mssv
            s["email"] = f"{mssv}@{_STUDENT_EMAIL_DOMAIN}"

    for s in raw:
        seed_id = int(s.get("id") or 0)
        s.setdefault("phone", _vn_phone_for(seed_id))

        # Normalize student email domain for DUT accounts.
        if s.get("email"):
            s["email"] = _with_email_domain(str(s["email"]), domain=_STUDENT_EMAIL_DOMAIN)

        # Keep both naming styles (seed-friendly + API-friendly)
        s.setdefault("faculty", s.get("major"))
        s.setdefault("year_of_study", s.get("year"))
        s.setdefault("research_interests", s.get("interests", []))

        # Ensure list fields exist (avoid None)
        s.setdefault("skills", [])
        s.setdefault("interests", [])
    return raw


def _normalize_lecturers(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for l in raw:
        seed_id = int(l.get("id") or 0)
        l.setdefault("phone", _vn_phone_for(500 + seed_id))
        l.setdefault("position", _lecturer_position_from_name(str(l.get("full_name") or "")))

        # Normalize lecturer email domain for DUT accounts.
        if l.get("email"):
            l["email"] = _with_email_domain(str(l["email"]), domain=_LECTURER_EMAIL_DOMAIN)

        # Optional fields used by the unified users table / UI
        l.setdefault("skills", [])
        l.setdefault("research_interests", [])
        l.setdefault("research_fields", [])
    return raw


def _deterministic_pick(pool: List[str], idx: int) -> str:
    if not pool:
        return ""
    return pool[idx % len(pool)]


def _deterministic_unique_student_ids(*, n: int, total_students: int, seed: int) -> List[int]:
    """Return `n` distinct student numeric IDs in range [1, total_students]."""
    if total_students <= 0:
        return []
    seen = set()
    out: List[int] = []
    stride = 7
    cursor = seed % total_students
    while len(out) < min(n, total_students):
        sid = (cursor % total_students) + 1
        if sid not in seen:
            seen.add(sid)
            out.append(sid)
        cursor += stride
        # If the stride cycles early due to gcd, nudge deterministically.
        if len(out) < n and len(out) == len(seen) and len(seen) > 0 and cursor % total_students == seed % total_students:
            cursor += 1
    return out


students = [
    {
        "id": 1,
        "full_name": "Nguyễn Minh Anh",
        "email": "minh.anh@sv.hcmut.edu.vn",
        "major": "Computer Science",
        "year": 3,
        "skills": ["Python", "Data Structures", "Algorithms", "SQL", "Docker"],
        "interests": ["AI", "Distributed Systems"],
        "career_orientation": "Aims to become a backend engineer focusing on scalable AI services.",
        "gpa": 3.6,
    },
    {
        "id": 2,
        "full_name": "Trần Quốc Bảo",
        "email": "quoc.bao@sv.hcmut.edu.vn",
        "major": "Data Science",
        "year": 4,
        "skills": ["Python", "Pandas", "Statistics", "Machine Learning", "Tableau"],
        "interests": ["AI", "NLP", "Social Media Analytics"],
        "career_orientation": "Wants to build data products for public sector decision making.",
        "gpa": 3.7,
    },
    {
        "id": 3,
        "full_name": "Lê Hoàng Duy",
        "email": "hoang.duy@sv.uit.edu.vn",
        "major": "Software Engineering",
        "year": 2,
        "skills": ["Java", "Spring Boot", "REST APIs", "PostgreSQL", "React"],
        "interests": ["Software Engineering", "Human-Computer Interaction"],
        "career_orientation": "Plans to specialize in full-stack systems for research platforms.",
        "gpa": 3.2,
    },
    {
        "id": 4,
        "full_name": "Phạm Thu Trang",
        "email": "thu.trang@sv.vnu.edu.vn",
        "major": "Environmental Science",
        "year": 3,
        "skills": ["GIS", "Remote Sensing", "Python", "ArcGIS", "Data Analysis"],
        "interests": ["Climate Change", "Water Quality", "Urban Ecology"],
        "career_orientation": "Aims to work on environmental monitoring and policy analytics.",
        "gpa": 3.4,
    },
    {
        "id": 5,
        "full_name": "Võ Hải Yến",
        "email": "hai.yen@sv.ump.edu.vn",
        "major": "Biotechnology",
        "year": 4,
        "skills": ["Bioinformatics", "R", "PCR", "Genomics", "Data Visualization"],
        "interests": ["Genetics", "Molecular Diagnostics"],
        "career_orientation": "Wants to pursue a PhD in translational genomics.",
        "gpa": 3.8,
    },
    {
        "id": 6,
        "full_name": "Bùi Gia Hân",
        "email": "gia.han@sv.hust.edu.vn",
        "major": "Artificial Intelligence",
        "year": 2,
        "skills": ["Python", "PyTorch", "Deep Learning", "Computer Vision", "Linux"],
        "interests": ["AI", "Medical Imaging"],
        "career_orientation": "Targets applied AI roles in healthcare startups.",
        "gpa": 3.5,
    },
    {
        "id": 7,
        "full_name": "Đặng Quang Huy",
        "email": "quang.huy@sv.hcmus.edu.vn",
        "major": "Applied Mathematics",
        "year": 3,
        "skills": ["MATLAB", "Optimization", "Linear Algebra", "Python", "Numerical Methods"],
        "interests": ["Operations Research", "Economics"],
        "career_orientation": "Intends to become a quantitative analyst.",
        "gpa": 3.3,
    },
    {
        "id": 8,
        "full_name": "Huỳnh Ngọc Mai",
        "email": "ngoc.mai@sv.uel.edu.vn",
        "major": "Business Analytics",
        "year": 4,
        "skills": ["SQL", "Power BI", "Excel", "Forecasting", "Python"],
        "interests": ["Economics", "Supply Chain", "Fintech"],
        "career_orientation": "Wants to build analytics models for logistics firms.",
        "gpa": 3.6,
    },
    {
        "id": 9,
        "full_name": "Phan Đức Thịnh",
        "email": "duc.thinh@sv.uit.edu.vn",
        "major": "Information Systems",
        "year": 2,
        "skills": ["SQL", "Data Modeling", "BPMN", "Python", "UI/UX Design"],
        "interests": ["Information Systems", "Digital Transformation"],
        "career_orientation": "Plans to become a product analyst for edu-tech.",
        "gpa": 3.1,
    },
    {
        "id": 10,
        "full_name": "Vũ Khánh Linh",
        "email": "khanh.linh@sv.hcmut.edu.vn",
        "major": "Data Science",
        "year": 3,
        "skills": ["Python", "Scikit-learn", "Data Cleaning", "NLP", "Jupyter"],
        "interests": ["NLP", "Education Analytics"],
        "career_orientation": "Aims to build Vietnamese language learning tools.",
        "gpa": 3.7,
    },
    {
        "id": 11,
        "full_name": "Trương Thành Long",
        "email": "thanh.long@sv.dut.udn.vn",
        "major": "Electrical Engineering",
        "year": 4,
        "skills": ["Embedded Systems", "C", "IoT", "Signal Processing", "PCB Design"],
        "interests": ["Smart Sensors", "Energy Systems"],
        "career_orientation": "Wants to design resilient IoT infrastructure.",
        "gpa": 3.2,
    },
    {
        "id": 12,
        "full_name": "Đỗ Nhật Nam",
        "email": "nhat.nam@sv.hcmus.edu.vn",
        "major": "Computer Science",
        "year": 1,
        "skills": ["Python", "HTML/CSS", "JavaScript", "Git", "Data Analysis"],
        "interests": ["AI", "EdTech"],
        "career_orientation": "Exploring research on adaptive learning systems.",
        "gpa": 3.0,
    },
    {
        "id": 13,
        "full_name": "Cao Thị Mỹ Linh",
        "email": "my.linh@sv.ump.edu.vn",
        "major": "Biomedical Engineering",
        "year": 3,
        "skills": ["Medical Imaging", "Python", "Signal Processing", "Statistics", "MATLAB"],
        "interests": ["Bio-signal Analysis", "AI in Healthcare"],
        "career_orientation": "Plans to work on AI-assisted diagnostics.",
        "gpa": 3.6,
    },
    {
        "id": 14,
        "full_name": "Lý Minh Khoa",
        "email": "minh.khoa@sv.hust.edu.vn",
        "major": "Computer Science",
        "year": 4,
        "skills": ["Go", "Distributed Systems", "Kubernetes", "PostgreSQL", "Docker"],
        "interests": ["Cloud Systems", "AI Infrastructure"],
        "career_orientation": "Aims to be an SRE for research platforms.",
        "gpa": 3.5,
    },
    {
        "id": 15,
        "full_name": "Tạ Thanh Tùng",
        "email": "thanh.tung@sv.vnu.edu.vn",
        "major": "Economics",
        "year": 2,
        "skills": ["Econometrics", "R", "Stata", "Data Visualization", "Python"],
        "interests": ["Development Economics", "Climate Policy"],
        "career_orientation": "Wants to analyze climate finance impacts.",
        "gpa": 3.3,
    },
    {
        "id": 16,
        "full_name": "Ngô Thảo Vy",
        "email": "thao.vy@sv.uel.edu.vn",
        "major": "Marketing Analytics",
        "year": 3,
        "skills": ["A/B Testing", "SQL", "Google Analytics", "Python", "Visualization"],
        "interests": ["Consumer Behavior", "Recommender Systems"],
        "career_orientation": "Targets data-driven marketing research.",
        "gpa": 3.4,
    },
    {
        "id": 17,
        "full_name": "Đinh Đức Mạnh",
        "email": "duc.manh@sv.hcmut.edu.vn",
        "major": "Artificial Intelligence",
        "year": 4,
        "skills": ["Python", "TensorFlow", "Reinforcement Learning", "MLOps", "Docker"],
        "interests": ["Robotics", "Smart Manufacturing"],
        "career_orientation": "Aims to build AI control systems in factories.",
        "gpa": 3.8,
    },
    {
        "id": 18,
        "full_name": "Mai Phương Anh",
        "email": "phuong.anh@sv.hcmus.edu.vn",
        "major": "Environmental Science",
        "year": 1,
        "skills": ["Python", "Data Collection", "GIS", "Climate Modeling", "Excel"],
        "interests": ["Climate Change", "Biodiversity"],
        "career_orientation": "Wants to contribute to conservation data work.",
        "gpa": 3.1,
    },
    {
        "id": 19,
        "full_name": "Lâm Hoài An",
        "email": "hoai.an@sv.uit.edu.vn",
        "major": "Software Engineering",
        "year": 3,
        "skills": ["Node.js", "TypeScript", "React", "API Design", "PostgreSQL"],
        "interests": ["HCI", "Digital Health"],
        "career_orientation": "Plans to build user-centered research portals.",
        "gpa": 3.4,
    },
    {
        "id": 20,
        "full_name": "Quách Tấn Phúc",
        "email": "tan.phuc@sv.dut.udn.vn",
        "major": "Mechanical Engineering",
        "year": 4,
        "skills": ["CAD", "Python", "Simulation", "Control Systems", "MATLAB"],
        "interests": ["Robotics", "Automation"],
        "career_orientation": "Wants to integrate AI into mechanical design.",
        "gpa": 3.2,
    },
    {
        "id": 21,
        "full_name": "Hồ Minh Triết",
        "email": "minh.triet@sv.hust.edu.vn",
        "major": "Data Science",
        "year": 2,
        "skills": ["Python", "SQL", "Data Mining", "Statistics", "Tableau"],
        "interests": ["Finance", "Risk Modeling"],
        "career_orientation": "Aims for a career in risk analytics.",
        "gpa": 3.5,
    },
    {
        "id": 22,
        "full_name": "Châu Bảo Ngọc",
        "email": "bao.ngoc@sv.ump.edu.vn",
        "major": "Biotechnology",
        "year": 2,
        "skills": ["Genomics", "R", "Laboratory Techniques", "Data Analysis", "Bioinformatics"],
        "interests": ["Microbiome", "Genetics"],
        "career_orientation": "Targets research in microbial genomics.",
        "gpa": 3.4,
    },
    {
        "id": 23,
        "full_name": "Phùng Quốc Khánh",
        "email": "quoc.khanh@sv.hcmut.edu.vn",
        "major": "Information Systems",
        "year": 3,
        "skills": ["Business Process Modeling", "SQL", "Python", "Power BI", "Requirements Analysis"],
        "interests": ["Digital Transformation", "Public Services"],
        "career_orientation": "Wants to modernize government data systems.",
        "gpa": 3.3,
    },
    {
        "id": 24,
        "full_name": "Dương Mỹ An",
        "email": "my.an@sv.vnu.edu.vn",
        "major": "Economics",
        "year": 4,
        "skills": ["Time Series Forecasting", "R", "Python", "Econometrics", "Policy Analysis"],
        "interests": ["Labor Economics", "Education Policy"],
        "career_orientation": "Plans to work on evidence-based policy.",
        "gpa": 3.7,
    },
    {
        "id": 25,
        "full_name": "Tô Gia Huy",
        "email": "gia.huy@sv.uit.edu.vn",
        "major": "Computer Science",
        "year": 2,
        "skills": ["C++", "Algorithms", "Computer Vision", "OpenCV", "Python"],
        "interests": ["Autonomous Systems", "AI Safety"],
        "career_orientation": "Aims to research safe computer vision systems.",
        "gpa": 3.2,
    },
]


# ==================== EXTRA STUDENTS (BULK) ====================
# Add many more student accounts for realistic project/application volumes.
_FIRST_NAMES = [
    "An", "Anh", "Bảo", "Châu", "Duy", "Giang", "Hân", "Huy", "Khoa", "Linh",
    "Long", "Mai", "Nam", "Ngọc", "Phúc", "Quân", "Trang", "Thảo", "Thịnh", "Tú",
    "Uyên", "Vy", "Yến", "Minh", "Phương",
]
_LAST_NAMES = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Võ", "Đặng", "Huỳnh", "Phan", "Đỗ", "Dương",
    "Cao", "Tạ", "Ngô", "Mai", "Lý", "Bùi", "Hồ", "Châu", "Quách", "Trương",
]

_MAJORS = [
    "Computer Science",
    "Software Engineering",
    "Data Science",
    "Information Systems",
    "Artificial Intelligence",
    "Business Analytics",
    "Applied Mathematics",
    "Environmental Science",
    "Biotechnology",
    "Electrical Engineering",
]

_MAJOR_SKILLS = {
    "Computer Science": ["Python", "Data Structures", "Algorithms", "SQL", "Git"],
    "Software Engineering": ["Java", "REST APIs", "PostgreSQL", "Docker", "Testing"],
    "Data Science": ["Python", "Pandas", "Statistics", "Machine Learning", "Data Visualization"],
    "Information Systems": ["SQL", "Data Modeling", "BPMN", "Power BI", "Requirements Analysis"],
    "Artificial Intelligence": ["Python", "PyTorch", "Deep Learning", "NLP", "Computer Vision"],
    "Business Analytics": ["SQL", "Excel", "Forecasting", "Power BI", "Python"],
    "Applied Mathematics": ["Optimization", "Linear Algebra", "Numerical Methods", "Python", "MATLAB"],
    "Environmental Science": ["GIS", "Remote Sensing", "Python", "Data Analysis", "Climate Modeling"],
    "Biotechnology": ["Bioinformatics", "Genomics", "PCR", "Data Analysis", "R"],
    "Electrical Engineering": ["Embedded Systems", "C", "IoT", "Signal Processing", "PCB Design"],
}

_MAJOR_INTERESTS = {
    "Computer Science": ["Distributed Systems", "AI", "EdTech"],
    "Software Engineering": ["HCI", "DevOps", "Software Architecture"],
    "Data Science": ["NLP", "Analytics", "Fintech"],
    "Information Systems": ["Digital Transformation", "Product Analytics", "Data Governance"],
    "Artificial Intelligence": ["AI", "Robotics", "Medical Imaging"],
    "Business Analytics": ["Supply Chain", "Economics", "Forecasting"],
    "Applied Mathematics": ["Operations Research", "Economics", "Optimization"],
    "Environmental Science": ["Climate Change", "Water Quality", "Biodiversity"],
    "Biotechnology": ["Genetics", "Molecular Diagnostics", "Microbiome"],
    "Electrical Engineering": ["Smart Sensors", "Energy Systems", "Edge Computing"],
}

_STUDENT_EMAIL_DOMAINS = [
    _STUDENT_EMAIL_DOMAIN,
]

_EXTRA_STUDENTS_COUNT = 120
_base_student_max_id = max(s.get("id", 0) for s in students)
for i in range(1, _EXTRA_STUDENTS_COUNT + 1):
    sid = _base_student_max_id + i
    major = _deterministic_pick(_MAJORS, sid)
    first = _deterministic_pick(_FIRST_NAMES, sid)
    last = _deterministic_pick(_LAST_NAMES, sid * 3)
    mid = _deterministic_pick(["Văn", "Thị", "Minh", "Gia", "Hoàng", "Thanh"], sid * 5)
    full_name = f"{last} {mid} {first}".replace("  ", " ")
    domain = _deterministic_pick(_STUDENT_EMAIL_DOMAINS, sid)
    email = f"student{sid}@{domain}"
    year = 1 + (sid % 4)
    skills = list(_MAJOR_SKILLS.get(major, []))
    interests = list(_MAJOR_INTERESTS.get(major, []))
    gpa = round(3.0 + ((sid % 9) * 0.1), 2)
    students.append(
        {
            "id": sid,
            "full_name": full_name,
            "email": email,
            "major": major,
            "year": year,
            "skills": skills,
            "interests": interests,
            "career_orientation": f"Mong muốn áp dụng kiến thức {major} vào đề tài thực tế và xây dựng hồ sơ học thuật vững chắc.",
            "gpa": gpa,
        }
    )


# ==================== SKILLS LIBRARY SEED ====================
# NOTE: keep this list as *data only*. It is consumed by backend/seed.py
# and inserted/upserted into the `skills_library` table.
skills_library: List[Dict[str, Any]] = [
    # Programming Languages
    {"name": "Python", "category": "Programming", "popularity_score": 100},
    {"name": "JavaScript", "category": "Programming", "popularity_score": 98},
    {"name": "TypeScript", "category": "Programming", "popularity_score": 90},
    {"name": "Java", "category": "Programming", "popularity_score": 88},
    {"name": "C", "category": "Programming", "popularity_score": 75},
    {"name": "C++", "category": "Programming", "popularity_score": 80},
    {"name": "C#", "category": "Programming", "popularity_score": 78},
    {"name": "Go", "category": "Programming", "popularity_score": 70},
    {"name": "Rust", "category": "Programming", "popularity_score": 60},
    {"name": "PHP", "category": "Programming", "popularity_score": 55},
    {"name": "Ruby", "category": "Programming", "popularity_score": 45},
    {"name": "Kotlin", "category": "Programming", "popularity_score": 58},
    {"name": "Swift", "category": "Programming", "popularity_score": 55},
    {"name": "R", "category": "Programming", "popularity_score": 65},
    {"name": "MATLAB", "category": "Programming", "popularity_score": 50},
    {"name": "Scala", "category": "Programming", "popularity_score": 35},
    {"name": "Dart", "category": "Programming", "popularity_score": 40},
    {"name": "SQL", "category": "Database", "popularity_score": 95},

    # Web Fundamentals
    {"name": "HTML", "category": "Web", "popularity_score": 92},
    {"name": "CSS", "category": "Web", "popularity_score": 90},
    {"name": "REST APIs", "category": "Web", "popularity_score": 90},
    {"name": "GraphQL", "category": "Web", "popularity_score": 55},
    {"name": "WebSockets", "category": "Web", "popularity_score": 45},

    # Frontend
    {"name": "React", "category": "Frontend", "popularity_score": 90},
    {"name": "Next.js", "category": "Frontend", "popularity_score": 70},
    {"name": "Vue.js", "category": "Frontend", "popularity_score": 65},
    {"name": "Angular", "category": "Frontend", "popularity_score": 55},
    {"name": "Svelte", "category": "Frontend", "popularity_score": 35},
    {"name": "Redux", "category": "Frontend", "popularity_score": 45},
    {"name": "Tailwind CSS", "category": "Frontend", "popularity_score": 55},
    {"name": "Webpack", "category": "Frontend", "popularity_score": 35},
    {"name": "Vite", "category": "Frontend", "popularity_score": 45},

    # Backend Frameworks
    {"name": "Flask", "category": "Backend", "popularity_score": 60},
    {"name": "FastAPI", "category": "Backend", "popularity_score": 70},
    {"name": "Django", "category": "Backend", "popularity_score": 65},
    {"name": "Node.js", "category": "Backend", "popularity_score": 85},
    {"name": "Express.js", "category": "Backend", "popularity_score": 75},
    {"name": "Spring Boot", "category": "Backend", "popularity_score": 60},
    {"name": ".NET", "category": "Backend", "popularity_score": 55},
    {"name": "Gin", "category": "Backend", "popularity_score": 30},

    # Databases
    {"name": "PostgreSQL", "category": "Database", "popularity_score": 85},
    {"name": "MySQL", "category": "Database", "popularity_score": 75},
    {"name": "SQLite", "category": "Database", "popularity_score": 55},
    {"name": "MongoDB", "category": "Database", "popularity_score": 65},
    {"name": "Redis", "category": "Database", "popularity_score": 60},
    {"name": "Elasticsearch", "category": "Database", "popularity_score": 40},
    {"name": "pgvector", "category": "Database", "popularity_score": 35},

    # DevOps / Infra
    {"name": "Docker", "category": "DevOps", "popularity_score": 85},
    {"name": "Docker Compose", "category": "DevOps", "popularity_score": 70},
    {"name": "Kubernetes", "category": "DevOps", "popularity_score": 60},
    {"name": "Linux", "category": "DevOps", "popularity_score": 75},
    {"name": "Nginx", "category": "DevOps", "popularity_score": 55},
    {"name": "CI/CD", "category": "DevOps", "popularity_score": 55},
    {"name": "GitHub Actions", "category": "DevOps", "popularity_score": 45},
    {"name": "Git", "category": "DevOps", "popularity_score": 90},

    # Data Science / ML
    {"name": "NumPy", "category": "Data", "popularity_score": 70},
    {"name": "Pandas", "category": "Data", "popularity_score": 75},
    {"name": "Matplotlib", "category": "Data", "popularity_score": 55},
    {"name": "Seaborn", "category": "Data", "popularity_score": 40},
    {"name": "Scikit-learn", "category": "ML", "popularity_score": 70},
    {"name": "TensorFlow", "category": "ML", "popularity_score": 55},
    {"name": "PyTorch", "category": "ML", "popularity_score": 60},
    {"name": "NLP", "category": "ML", "popularity_score": 50},
    {"name": "Computer Vision", "category": "ML", "popularity_score": 45},
    {"name": "MLOps", "category": "ML", "popularity_score": 40},
    {"name": "A/B Testing", "category": "Data", "popularity_score": 35},
    {"name": "Statistics", "category": "Data", "popularity_score": 55},
    {"name": "Data Visualization", "category": "Data", "popularity_score": 45},
    {"name": "Power BI", "category": "Data", "popularity_score": 35},
    {"name": "Tableau", "category": "Data", "popularity_score": 30},

    # Security
    {"name": "OAuth2", "category": "Security", "popularity_score": 35},
    {"name": "JWT", "category": "Security", "popularity_score": 40},
    {"name": "OWASP Top 10", "category": "Security", "popularity_score": 25},
    {"name": "SQL Injection Prevention", "category": "Security", "popularity_score": 25},
    {"name": "XSS Prevention", "category": "Security", "popularity_score": 20},

    # Testing
    {"name": "Unit Testing", "category": "Testing", "popularity_score": 40},
    {"name": "Integration Testing", "category": "Testing", "popularity_score": 30},
    {"name": "pytest", "category": "Testing", "popularity_score": 35},
    {"name": "Postman", "category": "Testing", "popularity_score": 25},

    # Soft skills
    {"name": "Communication", "category": "Soft Skills", "popularity_score": 30},
    {"name": "Teamwork", "category": "Soft Skills", "popularity_score": 30},
    {"name": "Problem Solving", "category": "Soft Skills", "popularity_score": 35},
    {"name": "Time Management", "category": "Soft Skills", "popularity_score": 25},
    {"name": "Critical Thinking", "category": "Soft Skills", "popularity_score": 25},
]

# Expand the library to ~220 skills with common ecosystem entries.
# Kept as deterministic data generation (no randomness) to keep seed stable.
_extra_skills = [
    # Frontend ecosystem
    ("React Router", "Frontend"), ("Zustand", "Frontend"), ("MobX", "Frontend"),
    ("Sass", "Frontend"), ("Less", "Frontend"), ("Storybook", "Frontend"),
    ("Jest", "Testing"), ("Playwright", "Testing"), ("Cypress", "Testing"),

    # Backend ecosystem
    ("SQLAlchemy", "Backend"), ("Alembic", "Backend"), ("Celery", "Backend"),
    ("RabbitMQ", "DevOps"), ("Kafka", "DevOps"),

    # Data/ML ecosystem
    ("Jupyter", "Data"), ("ETL", "Data"), ("Data Warehousing", "Data"),
    ("Airflow", "Data"), ("dbt", "Data"),
    ("LangChain", "ML"), ("Transformers", "ML"), ("Sentence Transformers", "ML"),
    ("Vector Search", "ML"), ("RAG", "ML"),

    # Cloud
    ("AWS", "Cloud"), ("GCP", "Cloud"), ("Azure", "Cloud"),
    ("S3", "Cloud"), ("Cloud Run", "Cloud"), ("Cloud Functions", "Cloud"),
    ("Terraform", "DevOps"), ("Ansible", "DevOps"),

    # Mobile
    ("Android", "Mobile"), ("iOS", "Mobile"), ("Flutter", "Mobile"),
    ("React Native", "Mobile"),

    # Databases / data stores
    ("TimescaleDB", "Database"), ("DynamoDB", "Database"), ("Firestore", "Database"),
    ("Cassandra", "Database"),

    # Observability
    ("Logging", "Observability"), ("Monitoring", "Observability"),
    ("Prometheus", "Observability"), ("Grafana", "Observability"),
    ("OpenTelemetry", "Observability"),

    # Research / domain
    ("Distributed Systems", "Research"), ("Recommender Systems", "Research"),
    ("Information Retrieval", "Research"), ("Optimization", "Research"),
    ("Linear Algebra", "Research"), ("Signal Processing", "Research"),

    # Tooling
    ("VS Code", "Tooling"), ("Linux Shell", "DevOps"), ("Bash", "DevOps"),
    ("PowerShell", "DevOps"),

    # More frontend / UI
    ("D3.js", "Frontend"), ("Chart.js", "Frontend"), ("Three.js", "Frontend"),
    ("Material UI", "Frontend"), ("Ant Design", "Frontend"),
    ("Accessibility (a11y)", "Frontend"), ("SEO", "Web"),
    ("Responsive Design", "Frontend"),

    # API / Architecture
    ("OpenAPI", "Web"), ("Swagger", "Web"), ("gRPC", "Web"),
    ("Microservices", "Backend"), ("Monolith Architecture", "Backend"),
    ("Domain-Driven Design", "Backend"), ("Clean Architecture", "Backend"),
    ("Design Patterns", "Backend"),

    # Python ecosystem
    ("Pydantic", "Backend"), ("Uvicorn", "Backend"), ("Gunicorn", "Backend"),
    ("Werkzeug", "Backend"),

    # Java ecosystem
    ("Maven", "Backend"), ("Gradle", "Backend"),

    # DevOps / Platform
    ("Helm", "DevOps"), ("Argo CD", "DevOps"), ("Flux", "DevOps"),
    ("Istio", "DevOps"), ("Traefik", "DevOps"),
    ("HashiCorp Vault", "Security"), ("Keycloak", "Security"),
    ("Nexus Repository", "DevOps"), ("SonarQube", "DevOps"),

    # Observability tools
    ("Sentry", "Observability"), ("Datadog", "Observability"),
    ("New Relic", "Observability"),

    # Data engineering
    ("Apache Spark", "Data"), ("Hadoop", "Data"), ("Flink", "Data"),
    ("Data Modeling", "Data"), ("Dimensional Modeling", "Data"),
    ("BigQuery", "Data"), ("Snowflake", "Data"), ("Redshift", "Data"),
    ("Kafka Streams", "Data"),

    # ML tooling
    ("MLflow", "ML"), ("Weights & Biases", "ML"), ("DVC", "ML"),
    ("ONNX", "ML"), ("CUDA", "ML"),
    ("OpenCV", "ML"), ("spaCy", "ML"), ("Gensim", "ML"),
    ("XGBoost", "ML"), ("LightGBM", "ML"), ("CatBoost", "ML"),
    ("Keras", "ML"), ("Hugging Face", "ML"),

    # Vector DB / search
    ("FAISS", "ML"), ("Milvus", "Database"), ("Pinecone", "Database"),
    ("Weaviate", "Database"),

    # Security (more)
    ("Authentication", "Security"), ("Authorization", "Security"),
    ("RBAC", "Security"), ("Rate Limiting", "Security"),
    ("Threat Modeling", "Security"),

    # Project / product
    ("Agile", "Product"), ("Scrum", "Product"), ("Kanban", "Product"),
    ("Product Thinking", "Product"),

    # More soft skills
    ("Leadership", "Soft Skills"), ("Presentation", "Soft Skills"),
    ("Technical Writing", "Soft Skills"), ("Mentoring", "Soft Skills"),
    ("Negotiation", "Soft Skills"), ("Stakeholder Management", "Soft Skills"),

    # Domain skills (useful for cross-discipline matching)
    ("GIS", "Domain"), ("Remote Sensing", "Domain"),
    ("Bioinformatics", "Domain"), ("Genomics", "Domain"), ("PCR", "Domain"),
    ("IoT", "Domain"), ("Embedded Systems", "Domain"), ("PCB Design", "Domain"),
    ("BPMN", "Domain"), ("UI/UX Design", "Domain"),
]

_existing_names = {row["name"].strip().lower() for row in skills_library}
for idx, (name, cat) in enumerate(_extra_skills, start=1):
    key = name.strip().lower()
    if key in _existing_names:
        continue
    skills_library.append(
        {
            "name": name,
            "category": cat,
            "popularity_score": max(10, 60 - idx),
        }
    )
    _existing_names.add(key)

lecturers = [
    {
        "id": 1,
        "full_name": "PGS.TS. Nguyễn Thị Thanh Hương",
        "email": "huong.nguyen@hcmut.edu.vn",
        "department": "Computer Science",
        "research_fields": ["Machine Learning", "Computer Vision", "Medical Imaging"],
        "years_of_experience": 18,
        "bio": "PGS.TS. Hương leads a medical AI group focused on reliable imaging pipelines. Her recent work emphasizes model interpretability and clinician-in-the-loop validation. She has supervised multiple industry collaborations on diagnostic workflows.",
    },
    {
        "id": 2,
        "full_name": "TS. Trần Minh Quân",
        "email": "quan.tran@uit.edu.vn",
        "department": "Data Science",
        "research_fields": ["NLP", "Information Retrieval", "Vietnamese Linguistics"],
        "years_of_experience": 12,
        "bio": "TS. Quân specializes in Vietnamese language technologies and scalable search systems. His lab builds datasets and benchmarks for low-resource NLP. He regularly collaborates with digital libraries and education platforms.",
    },
    {
        "id": 3,
        "full_name": "TS. Lê Hoài Phương",
        "email": "phuong.le@hcmus.edu.vn",
        "department": "Environmental Science",
        "research_fields": ["Climate Modeling", "Urban Air Quality", "Remote Sensing"],
        "years_of_experience": 15,
        "bio": "TS. Phương studies urban climate impacts and air quality dynamics in rapidly growing cities. She integrates satellite data with ground sensors to inform local mitigation policy. Her projects frequently engage city planners and environmental agencies.",
    },
    {
        "id": 4,
        "full_name": "TS. Phạm Quỳnh Như",
        "email": "nhu.pham@ump.edu.vn",
        "department": "Biotechnology",
        "research_fields": ["Genomics", "Molecular Diagnostics", "Bioinformatics"],
        "years_of_experience": 10,
        "bio": "TS. Như works on genomics pipelines for infectious disease surveillance. Her team develops diagnostic assays with computational validation layers. She focuses on reproducibility and data stewardship in wet-lab collaborations.",
    },
    {
        "id": 5,
        "full_name": "PGS.TS. Võ Đức Long",
        "email": "long.vo@hust.edu.vn",
        "department": "Electrical Engineering",
        "research_fields": ["IoT Systems", "Sensor Networks", "Edge Computing"],
        "years_of_experience": 20,
        "bio": "PGS.TS. Long designs resilient sensor networks for environmental monitoring. His research bridges low-power hardware design with edge analytics. He has led multiple multi-site deployments across the Mekong region.",
    },
    {
        "id": 6,
        "full_name": "TS. Đặng Hải Yến",
        "email": "yen.dang@uel.edu.vn",
        "department": "Economics",
        "research_fields": ["Development Economics", "Behavioral Economics", "Policy Evaluation"],
        "years_of_experience": 9,
        "bio": "TS. Yến focuses on policy evaluation using field experiments and administrative data. She is particularly interested in education and energy access outcomes. Her work emphasizes transparent methodology and reproducible analysis.",
    },
    {
        "id": 7,
        "full_name": "TS. Bùi Anh Tuấn",
        "email": "tuan.bui@dut.udn.vn",
        "department": "Software Engineering",
        "research_fields": ["Software Architecture", "DevOps", "Cloud Platforms"],
        "years_of_experience": 14,
        "bio": "TS. Tuấn researches engineering productivity for data-intensive applications. He builds reference architectures for research platforms and MLOps tooling. His group partners with universities to modernize software delivery.",
    },
    {
        "id": 8,
        "full_name": "TS. Hồ Bảo Châu",
        "email": "chau.ho@vnu.edu.vn",
        "department": "Biomedical Engineering",
        "research_fields": ["Biomedical Signal Processing", "Wearable Devices", "AI in Healthcare"],
        "years_of_experience": 11,
        "bio": "TS. Châu develops wearable sensing systems for stress and rehabilitation monitoring. Her lab combines biosignal processing with lightweight ML models. She collaborates with clinics to validate real-world usability.",
    },
]


# ==================== EXTRA LECTURERS (BULK) ====================
_LECTURER_DEPTS = [
    ("Computer Science", ["Machine Learning", "Software Architecture", "Information Retrieval"]),
    ("Data Science", ["NLP", "Data Engineering", "Recommender Systems"]),
    ("Software Engineering", ["DevOps", "Cloud Platforms", "Testing"]),
    ("Environmental Science", ["Climate Modeling", "Remote Sensing", "Urban Ecology"]),
    ("Biotechnology", ["Genomics", "Bioinformatics", "Molecular Diagnostics"]),
    ("Economics", ["Policy Evaluation", "Development Economics", "Behavioral Economics"]),
    ("Electrical Engineering", ["IoT Systems", "Edge Computing", "Signal Processing"]),
]

_LECTURER_PREFIX = ["TS.", "PGS.TS.", "ThS."]
_LECTURER_FIRST = ["Hải", "Minh", "Quang", "Thu", "Lan", "Hương", "Phúc", "Tuấn", "Như", "Phương", "Khánh", "Châu"]
_LECTURER_LAST = ["Nguyễn", "Trần", "Lê", "Phạm", "Võ", "Đặng", "Bùi", "Hồ", "Ngô", "Đỗ", "Dương"]

_EXTRA_LECTURERS_COUNT = 16
_base_lecturer_max_id = max(l.get("id", 0) for l in lecturers)
for i in range(1, _EXTRA_LECTURERS_COUNT + 1):
    lid = _base_lecturer_max_id + i
    prefix = _deterministic_pick(_LECTURER_PREFIX, lid)
    last = _deterministic_pick(_LECTURER_LAST, lid * 2)
    first = _deterministic_pick(_LECTURER_FIRST, lid * 3)
    mid = _deterministic_pick(["Văn", "Thị", "Hoàng", "Minh", "Đức", "Thanh"], lid * 5)
    full_name = f"{prefix} {last} {mid} {first}".replace("  ", " ")
    dept, fields = _LECTURER_DEPTS[lid % len(_LECTURER_DEPTS)]
    email = f"lecturer{lid}@dut.udn.vn"
    bio = (
        f"{full_name} tập trung vào {fields[0].lower()} và {fields[1].lower()} với các triển khai thực tế trong phòng thí nghiệm. "
        "Nhóm nghiên cứu ưu tiên thí nghiệm tái lập (reproducible), tài liệu rõ ràng và kết quả đo lường được. "
        "Sinh viên được hướng dẫn từ khâu đặt vấn đề, thiết kế đánh giá đến trình bày kết quả cho các bên liên quan."
    )
    lecturers.append(
        {
            "id": lid,
            "full_name": full_name,
            "email": email,
            "department": dept,
            "research_fields": list(fields),
            "years_of_experience": 6 + (lid % 18),
            "bio": bio,
        }
    )

projects = [
    {
        "id": 1,
        "lecturer_id": 1,
        "title": "Diabetic Retinopathy Screening with Lightweight CNNs",
        "description": "Build a compact CNN pipeline for retinal image screening on limited hardware. The project will compare model compression strategies and evaluate performance on Vietnamese datasets.",
        "required_skills": ["Python", "PyTorch", "Computer Vision", "Data Preprocessing"],
        "field": "AI",
        "max_students": 3,
    },
    {
        "id": 2,
        "lecturer_id": 1,
        "title": "Automatic Liver Lesion Segmentation in CT",
        "description": "Develop a segmentation workflow for CT scans using attention-based architectures. Students will design annotation guidance and measure clinical agreement.",
        "required_skills": ["Python", "Deep Learning", "Medical Imaging", "Annotation Tools"],
        "field": "AI",
        "max_students": 2,
    },
    {
        "id": 3,
        "lecturer_id": 1,
        "title": "Explainable AI for X-ray Triage",
        "description": "Create an explainability layer for X-ray triage models to support clinical trust. The project includes saliency visualization and bias audits across patient groups.",
        "required_skills": ["Python", "Machine Learning", "Model Interpretability", "Data Visualization"],
        "field": "AI",
        "max_students": 3,
    },
    {
        "id": 4,
        "lecturer_id": 2,
        "title": "Vietnamese Clinical Text De-identification",
        "description": "Build a de-identification pipeline for Vietnamese clinical notes. The system will combine rule-based patterns with transformer models to remove sensitive entities.",
        "required_skills": ["Python", "NLP", "Regex", "Data Ethics"],
        "field": "AI",
        "max_students": 2,
    },
    {
        "id": 5,
        "lecturer_id": 2,
        "title": "Academic Paper Recommendation for Research Projects",
        "description": "Design a recommendation engine for matching students to related literature. The project explores vector search and relevance feedback in Vietnamese and English.",
        "required_skills": ["Python", "Information Retrieval", "Vector Search", "SQL"],
        "field": "AI",
        "max_students": 4,
    },
    {
        "id": 6,
        "lecturer_id": 2,
        "title": "Sentiment Tracking on Education Forums",
        "description": "Analyze sentiment trends in education discussion boards over time. Students will build a crawler, curate a dataset, and evaluate model drift.",
        "required_skills": ["Python", "NLP", "Data Analysis", "Web Scraping"],
        "field": "AI",
        "max_students": 3,
    },
    {
        "id": 7,
        "lecturer_id": 3,
        "title": "Urban Heat Island Mapping with Satellite Data",
        "description": "Create high-resolution heat maps from multi-spectral satellite images. The project includes validation with ground temperature sensors and seasonal comparisons.",
        "required_skills": ["GIS", "Remote Sensing", "Python", "Data Analysis"],
        "field": "Environment",
        "max_students": 3,
    },
    {
        "id": 8,
        "lecturer_id": 3,
        "title": "Air Quality Forecasting for Ho Chi Minh City",
        "description": "Develop a forecasting model for PM2.5 concentrations using meteorological data. The team will compare statistical baselines with ML approaches.",
        "required_skills": ["Time Series", "Python", "Statistics", "Data Visualization"],
        "field": "Environment",
        "max_students": 4,
    },
    {
        "id": 9,
        "lecturer_id": 3,
        "title": "Green Corridor Planning Support Tool",
        "description": "Build a spatial decision tool for identifying potential green corridors. Outputs will support city planners with scenario-based analysis.",
        "required_skills": ["GIS", "Spatial Analysis", "Python", "Policy Analysis"],
        "field": "Environment",
        "max_students": 2,
    },
    {
        "id": 10,
        "lecturer_id": 4,
        "title": "Genome Variant Annotation Pipeline for Dengue Studies",
        "description": "Implement a reproducible pipeline to annotate viral genome variants. Students will integrate public databases and produce summary reports for epidemiologists.",
        "required_skills": ["Bioinformatics", "Python", "Genomics", "Linux"],
        "field": "Biology",
        "max_students": 3,
    },
    {
        "id": 11,
        "lecturer_id": 4,
        "title": "qPCR Data Quality Assessment Tool",
        "description": "Create a quality control toolkit for qPCR experiments. The tool will flag outliers and standard curve deviations with clear visual diagnostics.",
        "required_skills": ["R", "Statistics", "Laboratory Workflow", "Data Visualization"],
        "field": "Biology",
        "max_students": 2,
    },
    {
        "id": 12,
        "lecturer_id": 4,
        "title": "Microbiome Diversity Analysis in Urban Water",
        "description": "Analyze microbiome diversity across urban water sites and seasons. The project uses metagenomic workflows and comparative statistics.",
        "required_skills": ["Bioinformatics", "R", "Metagenomics", "Data Cleaning"],
        "field": "Biology",
        "max_students": 3,
    },
    {
        "id": 13,
        "lecturer_id": 5,
        "title": "Edge-Based Flood Sensor Network",
        "description": "Design a low-power sensor network for flood monitoring with edge analytics. Students will prototype data compression and offline sync strategies.",
        "required_skills": ["Embedded Systems", "IoT", "C", "Python"],
        "field": "Environment",
        "max_students": 4,
    },
    {
        "id": 14,
        "lecturer_id": 5,
        "title": "Energy-Efficient Smart Classroom Monitoring",
        "description": "Develop a sensor dashboard for occupancy and energy usage. The system will optimize sampling rates while preserving data fidelity.",
        "required_skills": ["Sensors", "MQTT", "Python", "Data Analysis"],
        "field": "IoT",
        "max_students": 3,
    },
    {
        "id": 15,
        "lecturer_id": 5,
        "title": "Predictive Maintenance for Campus HVAC",
        "description": "Build a predictive maintenance model using vibration and temperature logs. The project includes anomaly detection and maintenance scheduling metrics.",
        "required_skills": ["Signal Processing", "Python", "Machine Learning", "Data Logging"],
        "field": "AI",
        "max_students": 2,
    },
    {
        "id": 16,
        "lecturer_id": 6,
        "title": "Household Energy Consumption Behavior Study",
        "description": "Analyze survey and billing data to identify behavioral patterns in energy use. The project will produce segmented insights and policy recommendations.",
        "required_skills": ["Econometrics", "R", "Survey Design", "Data Analysis"],
        "field": "Economics",
        "max_students": 4,
    },
    {
        "id": 17,
        "lecturer_id": 6,
        "title": "Impact Evaluation of Scholarship Programs",
        "description": "Estimate the causal effects of scholarships on student outcomes. Students will implement matching and difference-in-differences models.",
        "required_skills": ["Policy Evaluation", "Stata", "Statistics", "Causal Inference"],
        "field": "Economics",
        "max_students": 3,
    },
    {
        "id": 18,
        "lecturer_id": 6,
        "title": "Market Basket Analysis for Campus Services",
        "description": "Discover purchase patterns in campus service transactions. The project will develop association rules and visualize product bundling.",
        "required_skills": ["SQL", "Python", "Association Rules", "Visualization"],
        "field": "Economics",
        "max_students": 3,
    },
    {
        "id": 19,
        "lecturer_id": 7,
        "title": "Research Project Management Platform MVP",
        "description": "Build an MVP platform for managing research projects and applications. The system includes role-based access and project analytics dashboards.",
        "required_skills": ["Django", "React", "PostgreSQL", "REST APIs"],
        "field": "Software",
        "max_students": 4,
    },
    {
        "id": 20,
        "lecturer_id": 7,
        "title": "Automated Dataset Versioning with DVC",
        "description": "Implement dataset versioning workflows for multi-team research. Students will design storage patterns and CI checks for data integrity.",
        "required_skills": ["Python", "Git", "DVC", "Docker"],
        "field": "Software",
        "max_students": 2,
    },
    {
        "id": 21,
        "lecturer_id": 7,
        "title": "CI/CD Templates for ML Experiments",
        "description": "Create reusable CI/CD templates for ML experiment pipelines. The project focuses on reproducibility, testing, and artifact tracking.",
        "required_skills": ["GitHub Actions", "Docker", "Python", "Testing"],
        "field": "Software",
        "max_students": 3,
    },
    {
        "id": 22,
        "lecturer_id": 8,
        "title": "Wearable Stress Monitoring with PPG Signals",
        "description": "Develop signal processing and features for stress monitoring from PPG sensors. The system will be validated against short lab protocols.",
        "required_skills": ["Signal Processing", "Python", "Biomedical Sensors", "Data Analysis"],
        "field": "Biology",
        "max_students": 3,
    },
    {
        "id": 23,
        "lecturer_id": 8,
        "title": "Sleep Stage Classification from EEG",
        "description": "Build a classifier for sleep stage detection from EEG recordings. Students will compare handcrafted features and deep learning baselines.",
        "required_skills": ["Python", "Machine Learning", "EEG Processing", "Feature Engineering"],
        "field": "Biology",
        "max_students": 2,
    },
    {
        "id": 24,
        "lecturer_id": 8,
        "title": "Rehabilitation Exercise Feedback App",
        "description": "Prototype a feedback system for rehabilitation exercises using pose estimation. The project includes UX testing with clinicians and safety checks.",
        "required_skills": ["Mobile UX", "Python", "Computer Vision", "Pose Estimation"],
        "field": "AI",
        "max_students": 4,
    },

    # Additional topics for richer demo data
    {
        "id": 25,
        "lecturer_id": 7,
        "title": "Xác thực an toàn & RBAC cho cổng thông tin nghiên cứu",
        "description": "Xây dựng xác thực, phân quyền và RBAC cho cổng thông tin nghiên cứu. Đề tài bao gồm threat modeling và kiểm thử bảo mật cơ bản để giảm rủi ro lộ lọt dữ liệu.",
        "required_skills": ["Python", "Flask", "JWT", "OAuth2", "Security"],
        "field": "Software",
        "max_students": 3,
    },
    {
        "id": 26,
        "lecturer_id": 2,
        "title": "Hỏi đáp tiếng Việt trên quy định/quy chế nhà trường",
        "description": "Xây dựng prototype hỏi đáp tiếng Việt trên các văn bản quy định/quy chế bằng retrieval + reranking. Sinh viên sẽ đánh giá độ đúng, độ bám nguồn (faithfulness) và phân loại lỗi thường gặp.",
        "required_skills": ["Python", "NLP", "Information Retrieval", "Vector Search"],
        "field": "AI",
        "max_students": 4,
    },
    {
        "id": 27,
        "lecturer_id": 5,
        "title": "Phát hiện bất thường trên thiết bị biên cho luồng cảm biến",
        "description": "Phát triển giải pháp phát hiện bất thường nhẹ chạy trên edge cho luồng dữ liệu cảm biến. Đề tài so sánh baseline thống kê và mô hình ML đơn giản dưới ràng buộc tài nguyên.",
        "required_skills": ["IoT", "Python", "Signal Processing", "Embedded Systems"],
        "field": "IoT",
        "max_students": 3,
    },
    {
        "id": 28,
        "lecturer_id": 6,
        "title": "Dự báo nhu cầu năng lượng trong trường theo các kịch bản",
        "description": "Dự báo nhu cầu năng lượng và kiểm thử các giả định theo kịch bản (giá, lịch học/hoạt động). Sản phẩm gồm notebook báo cáo rõ ràng và trực quan hoá theo góc nhìn chính sách.",
        "required_skills": ["Time Series", "R", "Python", "Data Visualization"],
        "field": "Economics",
        "max_students": 3,
    },
    {
        "id": 29,
        "lecturer_id": 1,
        "title": "Giám sát chất lượng cho pipeline AI y tế",
        "description": "Xây dựng kiểm tra giám sát data drift và chất lượng mô hình trong pipeline AI y tế. Sinh viên thiết kế dashboard và ngưỡng cảnh báo, có thể dùng dữ liệu mô phỏng để tạo các tình huống drift.",
        "required_skills": ["Python", "MLOps", "Data Analysis", "Logging"],
        "field": "AI",
        "max_students": 3,
    },
    {
        "id": 30,
        "lecturer_id": 3,
        "title": "Bản đồ rủi ro ngập lụt từ dữ liệu mở",
        "description": "Kết hợp DEM/độ cao, sử dụng đất và dữ liệu mưa để xây bản đồ rủi ro ngập. Đề tài nhấn mạnh workflow GIS tái lập và bước kiểm định kết quả.",
        "required_skills": ["GIS", "Python", "Remote Sensing", "Data Cleaning"],
        "field": "Environment",
        "max_students": 4,
    },
]


# ==================== EXTRA PROJECTS (BULK) ====================
_PROJECT_TRACKS = [
    {
        "field": "AI",
        "titles": [
            "Hỏi đáp tăng cường truy hồi (RAG) cho tri thức trong trường",
            "Phân loại bền vững khi dữ liệu bị lệch phân phối",
            "Mô hình thị giác nhẹ cho thiết bị biên (edge)",
            "Bộ công cụ đánh giá vector search và phân tích lỗi",
        ],
        "skills": ["Python", "NLP", "Vector Search", "Transformers", "Data Analysis"],
    },
    {
        "field": "Software",
        "titles": [
            "Tự động hoá workflow nghiên cứu với CI/CD",
            "Observability (log/metric/trace) cho dịch vụ nghiên cứu",
            "API Gateway và rate limiting cho microservices",
            "Upload dữ liệu an toàn và quản trị dữ liệu cho phòng lab",
        ],
        "skills": ["Python", "Docker", "CI/CD", "Logging", "PostgreSQL"],
    },
    {
        "field": "Environment",
        "titles": [
            "Phát hiện biến động lớp phủ đất từ ảnh vệ tinh",
            "Pipeline hiệu chuẩn cảm biến chất lượng không khí đô thị",
            "Tích hợp và kiểm định dữ liệu thuỷ văn",
            "Dashboard rủi ro khí hậu phục vụ quy hoạch đô thị",
        ],
        "skills": ["GIS", "Python", "Remote Sensing", "Data Cleaning", "Data Visualization"],
    },
    {
        "field": "Biology",
        "titles": [
            "Pipeline genomics tái lập (reproducible) kèm quality gates",
            "Trích xuất đặc trưng biosignal và benchmarking",
            "Bộ công cụ QC dữ liệu phòng thí nghiệm và phát hiện ngoại lệ",
            "Phân tích so sánh microbiome theo mùa",
        ],
        "skills": ["Python", "R", "Bioinformatics", "Statistics", "Data Visualization"],
    },
    {
        "field": "Economics",
        "titles": [
            "Đánh giá tác động (causal impact) với báo cáo minh bạch",
            "Dự báo và phân tích kịch bản cho chương trình công",
            "Workflow làm sạch dữ liệu khảo sát và hiệu chỉnh trọng số",
            "Dashboard chính sách với chỉ số tái lập (reproducible)",
        ],
        "skills": ["Statistics", "Econometrics", "R", "Python", "Data Visualization"],
    },
    {
        "field": "IoT",
        "titles": [
            "Thu thập telemetry trên edge kèm đồng bộ offline",
            "Phát hiện bất thường luồng cảm biến trên edge",
            "Tối ưu chiến lược sampling tiết kiệm năng lượng",
            "Giám sát đa điểm đo dựa trên MQTT",
        ],
        "skills": ["IoT", "Embedded Systems", "Python", "Signal Processing", "Docker"],
    },
]


def _project_description(title: str, field: str, required_skills: List[str]) -> str:
    skills_text = ", ".join(required_skills[:4])
    return (
        f"Đề tài '{title}' thuộc lĩnh vực {field}. "
        "Sinh viên sẽ xác định mục tiêu đo lường được, xây dựng baseline tối thiểu và cải tiến dần dựa trên đánh giá có hệ thống. "
        "Sản phẩm gồm repo tái lập (reproducible), báo cáo kỹ thuật ngắn và demo thể hiện rõ trade-off/giới hạn. "
        f"Công nghệ/kỹ năng kỳ vọng: {skills_text}."
    )


# Giữ số lượng dự án vừa phải để admin load nhanh.
# Base projects currently include the handcrafted topics above (ids 1..30).
# This count adds more generated topics on top.
# Target total projects ~= 100.
_EXTRA_PROJECTS_COUNT = 70
_base_project_max_id = max(p.get("id", 0) for p in projects)
_lecturer_ids_all = [l.get("id") for l in lecturers if l.get("id")]
for i in range(1, _EXTRA_PROJECTS_COUNT + 1):
    pid = _base_project_max_id + i
    track = _PROJECT_TRACKS[pid % len(_PROJECT_TRACKS)]
    title_base = _deterministic_pick(track["titles"], pid)
    title = f"Đề tài {pid}: {title_base}"
    lecturer_id = int(_lecturer_ids_all[pid % len(_lecturer_ids_all)])
    required_skills = list(track["skills"])
    desc = _project_description(title_base, track["field"], required_skills)
    max_students = 2 + (pid % 3)  # 2..4
    projects.append(
        {
            "id": pid,
            "lecturer_id": lecturer_id,
            "title": title,
            "description": desc,
            "required_skills": required_skills,
            "field": track["field"],
            "max_students": max_students,
        }
    )

students = _normalize_students(students)
lecturers = _normalize_lecturers(lecturers)


# ==================== APPLICATIONS (STUDENT CANDIDATES) ====================
# Data-only fixtures consumed by backend/seed.py.
# Bulk applications are generated below to control per-project counts.
applications: List[Dict[str, Any]] = []


# ==================== BULK APPLICATIONS (PER PROJECT) ====================
# Generate enough applications so each project has ~5-6 applicants
# and 2-3 accepted members ("đã tham gia").
_all_project_ids = [int(p.get("id")) for p in projects if p.get("id")]
_total_students = len(students)

# Lookups for realistic caps/wording
_title_lookup = {int(p.get("id")): str(p.get("title") or "") for p in projects if p.get("id")}
_max_students_lookup = {
    int(p.get("id")): int(p.get("max_students") or 1)
    for p in projects
    if p.get("id")
}


def _lcg(seed: int) -> int:
    """Small deterministic PRNG (LCG) for stable seed generation."""
    return (1103515245 * seed + 12345) & 0x7FFFFFFF


def _apps_count_for_project(pid: int) -> int:
    """Realistic long-tail distribution of applications per project.

    For 100 projects, this yields roughly:
    - ~10%: 0 applications
    - ~45%: 1-3 applications
    - ~30%: 4-7 applications
    - ~12%: 8-12 applications
    - ~3%: 15-25 applications
    """
    r = _lcg(pid * 97)
    p = r % 100
    t = (r // 100) % 100

    if p < 10:
        return 0
    if p < 55:
        return 1 + (t % 3)  # 1-3
    if p < 85:
        return 4 + (t % 4)  # 4-7
    if p < 97:
        return 8 + (t % 5)  # 8-12
    return 15 + (t % 11)  # 15-25


def _accepted_count_for_project(pid: int, *, total_apps: int, max_students: int) -> int:
    if total_apps <= 0 or max_students <= 0:
        return 0

    r = _lcg(pid * 131)
    base = 0
    if total_apps >= 3:
        base = 1
    if total_apps >= 8:
        base = 2
    if total_apps >= 15:
        base = 3

    # Not every project reaches "accepted" even if there are applicants.
    if r % 6 == 0:
        base = max(0, base - 1)

    # If there are many applicants, ensure at least 1 accepted sometimes.
    if base == 0 and total_apps >= 10 and (r % 3 == 0):
        base = 1

    return min(max_students, base, total_apps)

for pid in _all_project_ids:
    total_apps = _apps_count_for_project(pid)

    max_students = _max_students_lookup.get(pid, 1)
    accepted_count = _accepted_count_for_project(
        pid,
        total_apps=total_apps,
        max_students=max_students,
    )

    picked_students = _deterministic_unique_student_ids(
        n=total_apps,
        total_students=_total_students,
        seed=pid * 13,
    )

    project_title = _title_lookup.get(pid) or "dự án"

    r = _lcg(pid * 17)
    for idx, sid in enumerate(picked_students):
        remaining_after_accepted = total_apps - accepted_count

        if idx < accepted_count:
            status = "accepted"
            score = 88 + ((r + idx) % 10)  # 88-97
        else:
            rel = idx - accepted_count

            # Diversify remaining statuses in a realistic mix
            if remaining_after_accepted >= 3 and rel == 0 and (r % 3 == 0):
                status = "shortlisted"
                score = 78 + (r % 10)  # 78-87
            elif remaining_after_accepted >= 2 and rel == 1 and (r % 2 == 0):
                status = "reviewing"
                score = 70 + (r % 12)  # 70-81
            else:
                # Some get rejected (with reasons) to test UI edge cases
                if ((pid + idx) % 7 == 0) and total_apps >= 4:
                    status = "rejected"
                    score = 25 + ((r + idx) % 30)  # 25-54
                else:
                    status = "pending"
                    score = 55 + ((r + idx) % 25)  # 55-79

        payload: Dict[str, Any] = {
            "student_id": sid,
            "project_id": pid,
            "status": status,
            "match_score": score,
            "application_text": (
                f"Em xin ứng tuyển vào '{project_title}'. "
                "Em sẽ chủ động cập nhật tiến độ hàng tuần, trao đổi rõ ràng và hoàn thành công việc đúng hạn. "
                "Em mong được thầy/cô góp ý để cải thiện chuyên môn và chất lượng sản phẩm."
            ),
        }

        if status == "rejected":
            reason = "Hiện tại hồ sơ/chuyên môn chưa phù hợp yêu cầu dự án. Bạn vui lòng bổ sung kỹ năng và ứng tuyển lại sau."
            payload["rejection_reason"] = reason
            payload["feedback_text"] = "Gợi ý: cập nhật kỹ năng liên quan và bổ sung minh chứng (mini project) để tăng điểm phù hợp."

        applications.append(payload)


student_skills = [
    {"student_id": student["id"], "skill": skill}
    for student in students
    for skill in (student.get("skills") or [])
]

student_interests = [
    {"student_id": student["id"], "interest": interest}
    for student in students
    for interest in (student.get("interests") or [])
]


__all__ = [
    "students",
    "lecturers",
    "projects",
    "applications",
    "student_skills",
    "student_interests",
    "skills_library",
]
        