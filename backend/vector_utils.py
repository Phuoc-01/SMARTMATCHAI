import numpy as np
from config import Config

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore[assignment]

# Load model once (optional)
model = SentenceTransformer(Config.MODEL_NAME) if SentenceTransformer else None

def get_embedding(text):
    """Convert text to vector embedding"""
    if isinstance(text, list):
        text = ' '.join(text)
    if model is None:
        return [0.0] * 384
    return model.encode(text, convert_to_numpy=True).tolist()

def calculate_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2)

def match_student_to_projects(student, projects):
    """Match student to projects based on skills and interests"""
    if not student.skill_vector:
        return []
    
    matches = []
    for project in projects:
        if project.requirement_vector and project.status == 'open':
            score = calculate_similarity(student.skill_vector, project.requirement_vector)
            matches.append({
                'project': project,
                'match_score': round(score * 100, 2)
            })
    
    # Sort by match score descending
    matches.sort(key=lambda x: x['match_score'], reverse=True)
    return matches
