"""
Production-ready AI Matching Service for SMART-MATCH AI
Using sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
"""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from functools import lru_cache
import json

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
import re
from collections import Counter

from .app import User, Project, Application, StudentSkill, Skill

logger = logging.getLogger(__name__)

class AIMatchingConfig:
    """Configuration for AI matching algorithm"""
    
    # Weight factors for different matching criteria
    SKILL_SIMILARITY_WEIGHT = 0.40
    INTEREST_ALIGNMENT_WEIGHT = 0.25
    EXPERIENCE_RELEVANCE_WEIGHT = 0.20
    TIMING_COMPATIBILITY_WEIGHT = 0.15
    
    # Skill verification level weights (3 levels)
    VERIFICATION_LEVEL_WEIGHTS = {
        1: 1.0,  # Lecturer verified
        2: 0.7,  # Evidence uploaded
        3: 0.4   # Self-declared
    }
    
    # Skill importance multipliers
    SKILL_IMPORTANCE_MULTIPLIERS = {
        "high": 1.2,
        "medium": 1.0,
        "low": 0.8
    }
    
    # Matching thresholds
    MIN_MATCH_SCORE = 30.0
    EXCELLENT_MATCH_THRESHOLD = 85.0
    GOOD_MATCH_THRESHOLD = 70.0
    FAIR_MATCH_THRESHOLD = 50.0
    
    # Cache settings
    VECTOR_CACHE_SIZE = 1000
    MATCH_CACHE_SIZE = 500

class SmartMatchAIService:
    """Main AI Matching Service for SMART-MATCH AI"""
    
    def __init__(self, config: Optional[AIMatchingConfig] = None):
        self.config = config or AIMatchingConfig()
        self._initialize_models()
        
        # Caches
        self._vector_cache = {}
        self._match_cache = {}
        
        # Skill taxonomy for normalization
        self._load_skill_taxonomy()
        
        logger.info("✅ SmartMatch AI Service initialized")
    
    def _initialize_models(self):
        """Initialize AI models with error handling"""
        try:
            logger.info("Loading AI models...")
            
            # Load multilingual sentence transformer
            self.embedding_model = SentenceTransformer(
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
            )
            self.vector_dimension = 384
            
            # Load spaCy for text processing (Vietnamese support)
            try:
                self.nlp = spacy.load("vi_core_news_sm")
            except:
                # Fallback to English model
                self.nlp = spacy.load("en_core_web_sm")
            
            logger.info(f"✅ AI models loaded successfully (dimension: {self.vector_dimension})")
            
        except Exception as e:
            logger.error(f"❌ Failed to load AI models: {e}")
            raise
    
    def _load_skill_taxonomy(self):
        """Load skill taxonomy for normalization"""
        self.skill_taxonomy = {
            # Programming Languages
            "python": ["python", "python3", "py", "python programming"],
            "java": ["java", "java programming", "jdk", "jre"],
            "javascript": ["javascript", "js", "es6", "typescript", "node.js", "nodejs"],
            "c++": ["c++", "cpp", "cplusplus"],
            "c#": ["c#", "csharp", ".net"],
            
            # Data Science & AI
            "machine learning": ["machine learning", "ml", "ai", "artificial intelligence"],
            "deep learning": ["deep learning", "neural networks", "cnn", "rnn"],
            "data science": ["data science", "data analysis", "data analytics"],
            "data visualization": ["data visualization", "data viz", "plotting", "charts"],
            "natural language processing": ["nlp", "natural language processing", "text mining"],
            "computer vision": ["computer vision", "cv", "image processing"],
            
            # Web Development
            "react": ["react", "reactjs", "react.js", "next.js"],
            "vue": ["vue", "vuejs", "vue.js"],
            "angular": ["angular", "angularjs"],
            "html/css": ["html", "css", "html5", "css3", "frontend"],
            "rest api": ["rest", "restful", "api", "web services"],
            
            # Databases
            "sql": ["sql", "mysql", "postgresql", "postgres", "database"],
            "mongodb": ["mongodb", "mongo", "nosql"],
            "redis": ["redis", "cache", "caching"],
            
            # DevOps & Cloud
            "docker": ["docker", "container", "dockerfile"],
            "kubernetes": ["kubernetes", "k8s", "container orchestration"],
            "aws": ["aws", "amazon web services", "ec2", "s3"],
            "azure": ["azure", "microsoft azure"],
            "git": ["git", "github", "gitlab", "version control"],
            
            # Research Skills
            "research methodology": ["research methods", "methodology", "experimental design"],
            "academic writing": ["academic writing", "paper writing", "scientific writing"],
            "statistical analysis": ["statistics", "statistical analysis", "hypothesis testing"],
            "literature review": ["literature review", "systematic review"],
            
            # Soft Skills
            "teamwork": ["teamwork", "collaboration", "team player"],
            "communication": ["communication", "presentation", "public speaking"],
            "problem solving": ["problem solving", "critical thinking", "analytical skills"],
            "time management": ["time management", "project management", "organization"],
        }
    
    @lru_cache(maxsize=1000)
    def _normalize_skill(self, skill: str) -> str:
        """Normalize skill name using taxonomy"""
        skill_lower = skill.lower().strip()
        
        # Check if skill is in taxonomy
        for normalized, variations in self.skill_taxonomy.items():
            if any(variant in skill_lower for variant in variations):
                return normalized
        
        # If not found, return cleaned original
        return re.sub(r'\s+', ' ', skill_lower).strip()
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text using NLP"""
        if not text:
            return []
        
        try:
            doc = self.nlp(text.lower())
            keywords = []
            
            for token in doc:
                # Extract meaningful keywords (nouns, proper nouns, adjectives)
                if (token.pos_ in ['NOUN', 'PROPN', 'ADJ'] and 
                    not token.is_stop and 
                    len(token.text) > 2 and
                    token.text.isalpha()):
                    keywords.append(token.lemma_)
            
            # Get most common keywords
            keyword_counts = Counter(keywords)
            return [kw for kw, _ in keyword_counts.most_common(max_keywords)]
            
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            # Fallback to simple word extraction
            words = re.findall(r'\b\w{3,}\b', text.lower())
            return list(set(words))[:max_keywords]
    
    def create_skill_vector(self, skills: List[str]) -> np.ndarray:
        """Create vector embedding from list of skills"""
        if not skills:
            return np.zeros(self.vector_dimension)
        
        # Generate cache key
        cache_key = hash(tuple(sorted(skills)))
        if cache_key in self._vector_cache:
            return self._vector_cache[cache_key]
        
        # Normalize skills
        normalized_skills = [self._normalize_skill(skill) for skill in skills]
        skills_text = " ".join(normalized_skills)
        
        # Create embedding
        embedding = self.embedding_model.encode(skills_text)
        
        # Cache result
        self._vector_cache[cache_key] = embedding
        
        return embedding
    
    def create_project_vector(self, project: Project) -> np.ndarray:
        """Create vector embedding for project"""
        # Combine project information
        text_parts = [
            project.title,
            project.description,
            " ".join(project.required_skills or []),
            " ".join(project.preferred_skills or []),
            project.research_field or "",
        ]
        
        project_text = " ".join(filter(None, text_parts))
        return self.embedding_model.encode(project_text)
    
    def create_student_vector(self, student: User) -> np.ndarray:
        """Create vector embedding for student"""
        # Combine student information
        text_parts = [
            " ".join(student.technical_skills or []),
            " ".join(student.soft_skills or []),
            student.major or "",
            student.faculty or "",
            student.bio or "",
        ]
        
        student_text = " ".join(filter(None, text_parts))
        return self.embedding_model.encode(student_text)
    
    def calculate_skill_match_score(
        self, 
        student_skills: List[str], 
        project_required_skills: List[str],
        student_skill_verifications: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Calculate skill matching score with verification levels
        """
        if not project_required_skills:
            return {
                "score": 0.0,
                "matched_skills": [],
                "missing_skills": [],
                "verification_details": {}
            }
        
        # Normalize all skills
        normalized_student_skills = [self._normalize_skill(s) for s in student_skills]
        normalized_required_skills = [self._normalize_skill(s) for s in project_required_skills]
        
        # Calculate skill matches with verification weights
        matched_skills = []
        missing_skills = []
        verification_details = {}
        total_weight = 0.0
        matched_count = 0
        
        for req_skill in normalized_required_skills:
            found = False
            max_verification_weight = 0.0
            best_match = None
            
            # Check each student skill for match
            for student_skill in normalized_student_skills:
                similarity = self._calculate_skill_similarity(req_skill, student_skill)
                
                if similarity > 0.7:  # Threshold for skill match
                    found = True
                    
                    # Get verification weight for this skill
                    verification_weight = self._get_skill_verification_weight(
                        student_skill, student_skill_verifications
                    )
                    
                    if verification_weight > max_verification_weight:
                        max_verification_weight = verification_weight
                        best_match = {
                            "skill": student_skill,
                            "similarity": similarity,
                            "verification_weight": verification_weight
                        }
            
            if found and best_match:
                matched_skills.append({
                    "required_skill": req_skill,
                    "matched_skill": best_match["skill"],
                    "similarity": best_match["similarity"],
                    "verification_weight": best_match["verification_weight"]
                })
                total_weight += best_match["verification_weight"]
                matched_count += 1
                
                verification_details[req_skill] = {
                    "matched_with": best_match["skill"],
                    "verification_weight": best_match["verification_weight"]
                }
            else:
                missing_skills.append(req_skill)
        
        # Calculate final score (0-100)
        if matched_count > 0:
            avg_weight = total_weight / matched_count
            coverage = matched_count / len(normalized_required_skills)
            score = (avg_weight * 0.7 + coverage * 0.3) * 100
        else:
            score = 0.0
        
        return {
            "score": min(score, 100.0),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "verification_details": verification_details,
            "matched_count": matched_count,
            "total_required": len(normalized_required_skills),
            "coverage_percentage": (matched_count / len(normalized_required_skills)) * 100 if normalized_required_skills else 0
        }
    
    def _calculate_skill_similarity(self, skill1: str, skill2: str) -> float:
        """Calculate similarity between two skills"""
        # Check for exact or partial match
        if skill1 == skill2:
            return 1.0
        
        # Check if one skill contains the other
        if skill1 in skill2 or skill2 in skill1:
            return 0.8
        
        # Check for common words
        words1 = set(skill1.split())
        words2 = set(skill2.split())
        common_words = words1.intersection(words2)
        
        if common_words:
            return len(common_words) / max(len(words1), len(words2))
        
        return 0.0
    
    def _get_skill_verification_weight(
        self, 
        skill: str, 
        verifications: Optional[List[Dict]] = None
    ) -> float:
        """
        Get verification weight for a skill
        Returns highest weight from available verifications
        """
        if not verifications:
            return self.config.VERIFICATION_LEVEL_WEIGHTS[3]  # Default to level 3
        
        max_weight = self.config.VERIFICATION_LEVEL_WEIGHTS[3]
        
        for verification in verifications:
            if verification.get("skill_name") == skill:
                level = verification.get("verification_level", 3)
                weight = self.config.VERIFICATION_LEVEL_WEIGHTS.get(level, 0.4)
                max_weight = max(max_weight, weight)
        
        return max_weight
    
    def calculate_comprehensive_match_score(
        self,
        student: User,
        project: Project,
        include_verifications: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive match score between student and project
        """
        # Generate cache key
        cache_key = f"{student.id}_{project.id}_{include_verifications}"
        if cache_key in self._match_cache:
            return self._match_cache[cache_key]
        
        # Get student skill verifications if needed
        student_verifications = None
        if include_verifications:
            # This would query the database for student's skill verifications
            pass
        
        # Calculate individual components
        skill_match = self.calculate_skill_match_score(
            student_skills=student.technical_skills or [],
            project_required_skills=project.required_skills or [],
            student_skill_verifications=student_verifications
        )
        
        # Calculate vector similarity
        student_vector = self.create_student_vector(student)
        project_vector = self.create_project_vector(project)
        vector_similarity = float(cosine_similarity(
            student_vector.reshape(1, -1), 
            project_vector.reshape(1, -1)
        )[0][0])
        
        # Convert vector similarity to 0-100 scale
        vector_score = (vector_similarity + 1) * 50  # Convert from [-1,1] to [0,100]
        
        # Calculate interest alignment (if student has research interests)
        interest_alignment = 0.0
        if student.research_interests and project.research_field:
            # Simple keyword matching for interests
            student_interests = set(student.research_interests)
            project_keywords = set(self._extract_keywords(project.description))
            
            if student_interests and project_keywords:
                common = student_interests.intersection(project_keywords)
                interest_alignment = len(common) / len(student_interests) * 100
        
        # Calculate timing compatibility
        timing_compatibility = 100.0  # Default to perfect compatibility
        
        # Calculate final weighted score
        final_score = (
            skill_match["score"] * self.config.SKILL_SIMILARITY_WEIGHT +
            vector_score * 0.3 +  # Vector similarity weight
            interest_alignment * self.config.INTEREST_ALIGNMENT_WEIGHT +
            timing_compatibility * self.config.TIMING_COMPATIBILITY_WEIGHT
        )
        
        # Ensure score is within bounds
        final_score = max(0.0, min(100.0, final_score))
        
        # Determine match level
        match_level = self._get_match_level(final_score)
        
        result = {
            "match_score": round(final_score, 2),
            "match_level": match_level,
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
            "recommendation": self._get_recommendation(final_score, skill_match),
            "calculated_at": datetime.now().isoformat()
        }
        
        # Cache result
        self._match_cache[cache_key] = result
        
        return result
    
    def _get_match_level(self, score: float) -> str:
        """Get match level based on score"""
        if score >= self.config.EXCELLENT_MATCH_THRESHOLD:
            return "excellent"
        elif score >= self.config.GOOD_MATCH_THRESHOLD:
            return "good"
        elif score >= self.config.FAIR_MATCH_THRESHOLD:
            return "fair"
        else:
            return "poor"
    
    def _get_recommendation(self, score: float, skill_match: Dict) -> str:
        """Get recommendation based on match score"""
        if score >= self.config.EXCELLENT_MATCH_THRESHOLD:
            return "Rất phù hợp - Khuyến nghị ứng tuyển"
        elif score >= self.config.GOOD_MATCH_THRESHOLD:
            missing_count = len(skill_match.get("missing_skills", []))
            if missing_count == 0:
                return "Phù hợp - Có thể ứng tuyển"
            else:
                return f"Khá phù hợp - Cần bổ sung {missing_count} kỹ năng"
        elif score >= self.config.FAIR_MATCH_THRESHOLD:
            return "Tương đối phù hợp - Cần cải thiện nhiều kỹ năng"
        else:
            return "Ít phù hợp - Không khuyến nghị ứng tuyển"
    
    def find_recommended_projects(
        self, 
        student: User, 
        projects: List[Project],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find recommended projects for a student
        """
        recommendations = []
        
        for project in projects:
            # Skip if project is not accepting applications
            if not self._is_project_available(project):
                continue
            
            # Calculate match score
            match_result = self.calculate_comprehensive_match_score(student, project)
            
            # Add to recommendations if above threshold
            if match_result["match_score"] >= self.config.MIN_MATCH_SCORE:
                recommendations.append({
                    "project": project.to_dict(),
                    "match_result": match_result,
                    "recommendation_score": match_result["match_score"]
                })
        
        # Sort by recommendation score
        recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
        
        return recommendations[:limit]
    
    def rank_applicants(
        self, 
        project: Project, 
        applicants: List[User]
    ) -> List[Dict[str, Any]]:
        """
        Rank applicants for a project
        """
        ranked_applicants = []
        
        for applicant in applicants:
            # Calculate match score
            match_result = self.calculate_comprehensive_match_score(applicant, project)
            
            ranked_applicants.append({
                "applicant": applicant.to_dict(),
                "match_result": match_result,
                "ranking_score": match_result["match_score"]
            })
        
        # Sort by ranking score
        ranked_applicants.sort(key=lambda x: x["ranking_score"], reverse=True)
        
        # Add ranking position
        for i, applicant in enumerate(ranked_applicants, 1):
            applicant["ranking_position"] = i
        
        return ranked_applicants
    
    def batch_calculate_match_scores(
        self,
        student_project_pairs: List[Tuple[User, Project]]
    ) -> List[Dict[str, Any]]:
        """
        Batch calculate match scores for multiple student-project pairs
        """
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
        """
        Update AI vectors for projects
        """
        updated_projects = []
        
        for project in projects:
            project.requirement_vector = self.create_project_vector(project)
            updated_projects.append(project)
        
        return updated_projects
    
    def update_user_vectors(self, users: List[User]) -> List[User]:
        """
        Update AI vectors for users
        """
        updated_users = []
        
        for user in users:
            user.skill_vector = self.create_student_vector(user)
            updated_users.append(user)
        
        return updated_users
    
    def _is_project_available(self, project: Project) -> bool:
        """Check if project is available for applications"""
        if project.status != "published":
            return False
        
        if project.application_deadline and project.application_deadline < datetime.now().date():
            return False
        
        if project.max_students and project.application_count >= project.max_students:
            return False
        
        return True
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics for monitoring"""
        return {
            "model_info": {
                "name": "paraphrase-multilingual-MiniLM-L12-v2",
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

# ==================== FACTORY FUNCTION ====================
def create_ai_matching_service() -> SmartMatchAIService:
    """Factory function to create AI matching service"""
    return SmartMatchAIService()