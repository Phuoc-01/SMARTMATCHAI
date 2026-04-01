import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore[assignment]

from models import db, Project, User, VerifiedSkill  # type: ignore[attr-defined]


def calculate_match_score(student_skills: List[str], project_skills: List[str]) -> float:
    """Calculate a basic match score (0-100) using skill overlap.

    This is intentionally lightweight so the API can return a meaningful score
    even when the AI engine (SentenceTransformer) is not ready.
    """

    student_norm = {
        s.strip().lower()
        for s in (student_skills or [])
        if isinstance(s, str) and s.strip()
    }
    project_norm = {
        s.strip().lower()
        for s in (project_skills or [])
        if isinstance(s, str) and s.strip()
    }

    if not student_norm or not project_norm:
        return 0.0

    overlap = len(student_norm.intersection(project_norm))
    score = (overlap / len(project_norm)) * 100.0
    return round(max(0.0, min(100.0, score)), 2)


@dataclass(frozen=True)
class SmartMatchConfig:
    MODEL_NAME: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2"))
    VECTOR_DIM: int = 384

    SKILL_SIMILARITY_WEIGHT: float = 0.6
    VECTOR_SIMILARITY_WEIGHT: float = 0.3
    INTEREST_ALIGNMENT_WEIGHT: float = 0.1
    TIMING_COMPATIBILITY_WEIGHT: float = 0.0

    EXCELLENT_MATCH_THRESHOLD: float = 85.0
    GOOD_MATCH_THRESHOLD: float = 70.0
    FAIR_MATCH_THRESHOLD: float = 50.0
    MIN_MATCH_SCORE: float = 60.0

    VERIFICATION_LEVEL_WEIGHTS: Optional[Dict[str, float]] = None

    def __post_init__(self):
        if self.VERIFICATION_LEVEL_WEIGHTS is None:
            object.__setattr__(
                self,
                "VERIFICATION_LEVEL_WEIGHTS",
                {
                    "beginner": 0.6,
                    "intermediate": 0.8,
                    "expert": 1.0
                }
            )


class SmartMatchAIService:
    def __init__(self, config: Optional[SmartMatchConfig] = None):
        self.config = config or SmartMatchConfig()
        # Allow the backend to run without the AI stack installed.
        self.model = SentenceTransformer(self.config.MODEL_NAME) if SentenceTransformer else None
        self.vector_dimension = self.config.VECTOR_DIM
        self._vector_cache: Dict[str, List[float]] = {}
        self._match_cache: Dict[str, Dict[str, Any]] = {}

    def invalidate_student_match_cache(self, student_id) -> int:
        """Remove cached match results for a given student.

        Cache keys are stored as `f"{student.id}:{project.id}"`.
        When a student updates skills/interests/vector, cached scores become stale.
        """

        prefix = f"{student_id}:"
        keys = [k for k in self._match_cache.keys() if k.startswith(prefix)]
        for k in keys:
            self._match_cache.pop(k, None)
        return len(keys)

    def get_embedding(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self.vector_dimension

        if self.model is None:
            # AI model dependency is missing; return a stable default vector.
            return [0.0] * self.vector_dimension

        cache_key = text.strip().lower()
        cached = self._vector_cache.get(cache_key)
        if cached is not None:
            return cached

        vector = self.model.encode(text, normalize_embeddings=True)
        vector_list = vector.astype(float).tolist()
        vector_list = self._ensure_vector_length(vector_list)
        self._vector_cache[cache_key] = vector_list
        return vector_list

    def create_student_vector(self, student: User) -> List[float]:
        verified = VerifiedSkill.query.filter_by(student_id=student.id, is_verified=True).all()
        verified_skills = [v.skill for v in verified if v.skill]
        parts: List[str] = []

        parts.extend(student.skills or [])
        parts.extend(verified_skills)
        parts.extend(student.research_interests or [])
        if student.faculty:
            parts.append(student.faculty)
        if student.department:
            parts.append(student.department)
        parts.extend(student.research_fields or [])

        text = " ".join([p for p in parts if p])
        return self.get_embedding(text)

    def create_project_vector(self, project: Project) -> List[float]:
        parts: List[str] = []
        if project.title:
            parts.append(project.title)
        if project.description:
            parts.append(project.description)
        if project.research_field:
            parts.append(project.research_field)

        parts.extend(project.required_skills or [])
        parts.extend(project.preferred_skills or [])
        parts.extend(project.keywords or [])

        if project.description:
            parts.extend(self._extract_keywords(project.description))

        text = " ".join([p for p in parts if p])
        return self.get_embedding(text)

    def calculate_comprehensive_match_score(self, student: User, project: Project) -> Dict[str, Any]:
        cache_key = f"{student.id}:{project.id}"
        cached = self._match_cache.get(cache_key)
        if cached is not None:
            return cached

        skill_match = self._calculate_skill_match(student, project)

        student_vector = self._get_or_create_vector(student.skill_vector, self.create_student_vector, student)
        project_vector = self._get_or_create_vector(project.requirement_vector, self.create_project_vector, project)
        # Avoid giving a misleading constant baseline score when either vector is empty.
        # If the student profile has no content (skills/interests/faculty...), the embedding
        # can be a near-zero vector and cosine similarity becomes undefined.
        student_norm = float(np.linalg.norm(student_vector))
        project_norm = float(np.linalg.norm(project_vector))
        if student_norm <= 1e-9 or project_norm <= 1e-9:
            vector_similarity = 0.0
            vector_score = 0.0
        else:
            vector_similarity = self._cosine_similarity(student_vector, project_vector)
            vector_score = (vector_similarity + 1.0) * 50.0

        interest_alignment = self._calculate_interest_alignment(student, project)
        timing_compatibility = self._calculate_timing_compatibility(project)

        final_score = (
            skill_match["score"] * self.config.SKILL_SIMILARITY_WEIGHT +
            vector_score * self.config.VECTOR_SIMILARITY_WEIGHT +
            interest_alignment * self.config.INTEREST_ALIGNMENT_WEIGHT +
            timing_compatibility * self.config.TIMING_COMPATIBILITY_WEIGHT
        )
        final_score = max(0.0, min(100.0, final_score))

        match_level = self._get_match_level(final_score)
        recommendation = self._get_recommendation(final_score, skill_match)

        match_details = {
            "score": round(final_score, 2),
            "skill_match": round(skill_match["score"], 2),
            "interest_match": round(interest_alignment, 2),
            "reason": recommendation
        }

        result = {
            "match_score": round(final_score, 2),
            "match_level": match_level,
            "match_details": match_details,
            "breakdown": {
                "skill_similarity": round(skill_match["score"], 2),
                "vector_similarity": round(vector_score, 2),
                "interest_alignment": round(interest_alignment, 2),
                "timing_compatibility": round(timing_compatibility, 2)
            },
            "skill_match_details": skill_match,
            "matched_skills_count": skill_match["matched_count"],
            "total_required_skills": skill_match["total_required"],
            "coverage_percentage": skill_match["coverage_percentage"],
            "missing_skills": skill_match["missing_skills"],
            "recommendation": recommendation,
            "calculated_at": datetime.now().isoformat()
        }

        self._match_cache[cache_key] = result
        return result

    def find_recommended_projects(
        self,
        student: User,
        projects: List[Project],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        recommendations = []

        for project in projects:
            if not self._is_project_available(project):
                continue

            match_result = self.calculate_comprehensive_match_score(student, project)
            if match_result["match_score"] >= self.config.MIN_MATCH_SCORE:
                recommendations.append({
                    "project": project.to_dict(),
                    "match_result": match_result,
                    "recommendation_score": match_result["match_score"]
                })

        recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return recommendations[:limit]

    def rank_applicants(self, project: Project, applicants: List[User]) -> List[Dict[str, Any]]:
        ranked_applicants = []

        for applicant in applicants:
            match_result = self.calculate_comprehensive_match_score(applicant, project)
            ranked_applicants.append({
                "applicant": applicant.to_dict(),
                "match_result": match_result,
                "ranking_score": match_result["match_score"]
            })

        ranked_applicants.sort(key=lambda x: x["ranking_score"], reverse=True)
        for i, applicant in enumerate(ranked_applicants, 1):
            applicant["ranking_position"] = i

        return ranked_applicants

    def batch_calculate_match_scores(
        self,
        student_project_pairs: List[Tuple[User, Project]]
    ) -> List[Dict[str, Any]]:
        results = []
        for student, project in student_project_pairs:
            match_result = self.calculate_comprehensive_match_score(student, project)
            results.append({
                "student_id": str(student.id),
                "project_id": str(project.id),
                "match_result": match_result
            })
        return results

    def update_project_vectors(self, projects: List[Project]) -> List[Project]:
        updated_projects = []

        for project in projects:
            if not self._has_valid_vector(project.requirement_vector):
                project.requirement_vector = self.create_project_vector(project)
                db.session.add(project)
            updated_projects.append(project)

        db.session.commit()
        return updated_projects

    def update_user_vectors(self, users: List[User]) -> List[User]:
        updated_users = []

        for user in users:
            user.skill_vector = self.create_student_vector(user)
            updated_users.append(user)

        return updated_users

    def _calculate_skill_match(self, student: User, project: Project) -> Dict[str, Any]:
        student_skills = {s.strip().lower() for s in (student.skills or []) if s}
        verified = VerifiedSkill.query.filter_by(student_id=student.id, is_verified=True).all()
        for v in verified:
            if v.skill:
                student_skills.add(v.skill.strip().lower())

        required_norm = {s.strip().lower() for s in (project.required_skills or []) if s}
        if not required_norm:
            return {
                "score": 0.0,
                "matched_count": 0,
                "total_required": 0,
                "coverage_percentage": 0.0,
                "missing_skills": [],
                "matched_skills": []
            }

        matched = sorted(student_skills.intersection(required_norm))
        missing = sorted(required_norm.difference(student_skills))
        score = (len(matched) / len(required_norm)) * 100

        return {
            "score": round(score, 2),
            "matched_count": len(matched),
            "total_required": len(required_norm),
            "coverage_percentage": round(score, 2),
            "missing_skills": missing,
            "matched_skills": matched
        }

    def _calculate_interest_alignment(self, student: User, project: Project) -> float:
        if not student.research_interests:
            return 0.0

        student_interests = {s.strip().lower() for s in student.research_interests if s}
        project_keywords = set(self._extract_keywords(project.description or ""))
        if project.research_field:
            project_keywords.add(project.research_field.strip().lower())

        if not student_interests or not project_keywords:
            return 0.0

        common = student_interests.intersection(project_keywords)
        return (len(common) / len(student_interests)) * 100

    def _calculate_timing_compatibility(self, project: Project) -> float:
        deadline = getattr(project, "deadline", None)
        if deadline and deadline < datetime.now().date():
            return 0.0
        return 100.0

    def _get_or_create_vector(self, vector_value, creator, obj) -> np.ndarray:
        if self._has_valid_vector(vector_value):
            return np.array(vector_value, dtype=float)

        created = creator(obj)
        return np.array(created, dtype=float)

    def _has_valid_vector(self, vector_value) -> bool:
        if vector_value is None:
            return False
        arr = np.array(vector_value, dtype=float)
        if arr.size != self.vector_dimension:
            return False
        return bool(np.linalg.norm(arr) > 1e-9)

    def _ensure_vector_length(self, vector: List[float]) -> List[float]:
        if len(vector) == self.vector_dimension:
            return vector
        if len(vector) > self.vector_dimension:
            return vector[:self.vector_dimension]
        return vector + [0.0] * (self.vector_dimension - len(vector))

    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        denom = (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
        if denom <= 1e-12:
            return 0.0
        return float(np.dot(vec_a, vec_b) / denom)

    def _extract_keywords(self, text: str, limit: int = 20) -> List[str]:
        if not text:
            return []
        normalized = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        tokens = [t for t in normalized.split() if len(t) > 2]
        stopwords = {
            "the", "and", "for", "with", "from", "that", "this", "your",
            "you", "are", "was", "were", "have", "has", "had", "not",
            "can", "will", "may", "our", "their", "about", "into", "using",
            "use", "project", "student", "research", "system", "analysis",
            "data", "study"
        }
        keywords = [t for t in tokens if t not in stopwords]
        return keywords[:limit]

    def _get_match_level(self, score: float) -> str:
        if score >= self.config.EXCELLENT_MATCH_THRESHOLD:
            return "excellent"
        if score >= self.config.GOOD_MATCH_THRESHOLD:
            return "good"
        if score >= self.config.FAIR_MATCH_THRESHOLD:
            return "fair"
        return "poor"

    def _get_recommendation(self, score: float, skill_match: Dict[str, Any]) -> str:
        if score >= self.config.EXCELLENT_MATCH_THRESHOLD:
            return "Rat phu hop - Khuyen nghi ung tuyen"
        if score >= self.config.GOOD_MATCH_THRESHOLD:
            missing_count = len(skill_match.get("missing_skills", []))
            if missing_count == 0:
                return "Phu hop - Co the ung tuyen"
            return f"Kha phu hop - Can bo sung {missing_count} ky nang"
        if score >= self.config.FAIR_MATCH_THRESHOLD:
            return "Tuong doi phu hop - Can cai thien nhieu ky nang"
        return "It phu hop - Khong khuyen nghi ung tuyen"

    def _is_project_available(self, project: Project) -> bool:
        if project.status != "open":
            return False
        if getattr(project, "is_public", True) is False:
            return False
        deadline = getattr(project, "deadline", None)
        if deadline and deadline < datetime.now().date():
            return False
        max_students = getattr(project, "max_students", None)
        project_apps = getattr(project, "project_apps", None)
        if max_students and project_apps is not None:
            if len(project_apps) >= max_students:
                return False
        return True

    def get_system_stats(self) -> Dict[str, Any]:
        return {
            "model_info": {
                "name": self.config.MODEL_NAME,
                "dimension": self.vector_dimension,
                "cache_size": len(self._vector_cache)
            },
            "config": {
                "skill_similarity_weight": self.config.SKILL_SIMILARITY_WEIGHT,
                "verification_weights": self.config.VERIFICATION_LEVEL_WEIGHTS,
                "thresholds": {
                    "excellent": self.config.EXCELLENT_MATCH_THRESHOLD,
                    "good": self.config.GOOD_MATCH_THRESHOLD,
                    "fair": self.config.FAIR_MATCH_THRESHOLD,
                    "min": self.config.MIN_MATCH_SCORE
                }
            },
            "performance": {
                "vector_cache_hits": len(self._vector_cache),
                "match_cache_hits": len(self._match_cache)
            }
        }


def create_ai_matching_service() -> SmartMatchAIService:
    """Factory function to create AI matching service"""
    return SmartMatchAIService()