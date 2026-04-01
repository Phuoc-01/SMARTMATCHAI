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


def _vn_phone_for(seed_id: int) -> str:
    # Deterministic, valid-looking Vietnamese phone number (10 digits).
    # Example: 09 1234 5678
    return f"09{(10000000 + seed_id):08d}"


def _student_code_for(seed_id: int) -> str:
    # Keep compatibility with existing seed.py behavior.
    return str(102000000 + seed_id)


def _lecturer_position_from_name(full_name: str) -> str:
    # Extract common academic prefixes used in Vietnamese universities.
    match = re.match(r"^(PGS\.TS\.|GS\.TS\.|TS\.|ThS\.)\s+", (full_name or "").strip())
    if match:
        return match.group(1)
    return "Giảng viên"


def _normalize_students(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for s in raw:
        seed_id = int(s.get("id") or 0)
        s.setdefault("phone", _vn_phone_for(seed_id))

        # Keep both naming styles (seed-friendly + API-friendly)
        s.setdefault("faculty", s.get("major"))
        s.setdefault("year_of_study", s.get("year"))
        s.setdefault("student_id", _student_code_for(seed_id))
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

        # Optional fields used by the unified users table / UI
        l.setdefault("skills", [])
        l.setdefault("research_interests", [])
        l.setdefault("research_fields", [])
    return raw


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
]

students = _normalize_students(students)
lecturers = _normalize_lecturers(lecturers)


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
    "student_skills",
    "student_interests",
]
        