from typing import List
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")  # легка, якісна модель
    return _model

class EmbeddingsService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name

    def __call__(self, text: str) -> List[float]:
        model = _get_model()
        vec = model.encode(text, convert_to_numpy=True)
        return vec.tolist()