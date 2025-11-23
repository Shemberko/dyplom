from typing import List, Dict, Optional, Any, Tuple
import math

try:
    import numpy as np
except Exception:
    np = None

# імпорт клієнта до Neo4j, як у tasks.py
from services.neo4j.query_runner import query_runner as neo4j_client


def _l2_normalize(vec: List[float]) -> List[float]:
    v = [float(x) for x in vec]
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v] if norm > 0 else v


def _cosine_scores_py(query: List[float], candidates: List[List[float]]) -> List[float]:
    if not query:
        return [0.0] * len(candidates)
    q = [float(x) for x in query]
    qn = math.sqrt(sum(x * x for x in q))
    out = []
    for c in candidates:
        v = [float(x) for x in c]
        m = min(len(q), len(v))
        if m == 0 or qn == 0:
            out.append(0.0)
            continue
        vn = math.sqrt(sum(x * x for x in v[:m]))
        dot = sum(q[i] * v[i] for i in range(m))
        out.append(dot / (qn * vn) if vn != 0 else 0.0)
    return out


class RecommendationService:
    """
    Рекомендаційний сервіс: комбінує text & structural embeddings і повертає top-N сторінок.
    Використовує neo4j_client.run_query(...) як у tasks.py.
    """

    def __init__(self, client: Any = None):
        self.client = client or neo4j_client

    def _fetch_user_embeddings(self, user_id: str) -> Dict[str, Optional[List[float]]]:
        q = """
        MATCH (u:User {id: $user_id})
        RETURN u.textEmbedding AS text_emb, u.structuralEmbedding AS struct_emb
        """
        row = self.client.run_one(q, {"user_id": user_id}, write=False)
        if not row:
            return {"text": None, "structural": None}
        return {"text": row.get("text_emb"), "structural": row.get("struct_emb")}

    def _fetch_page_candidates(self, limit: int = 2000) -> List[Dict[str, Any]]:
        # Повертаємо сторінки з наявними ембедами та мінімальною метаінформацією
        q = """
        MATCH (p:Page)
        WHERE (p.structuralEmbedding IS NOT NULL OR p.text_embedding IS NOT NULL OR p.textEmbedding IS NOT NULL)
        RETURN elementId(p) AS elementId, p.id AS id, p.url AS url,
               p.structuralEmbedding AS structural, COALESCE(p.text_embedding, p.textEmbedding) AS text,
               p.title AS title, p.imageUrl AS image
        LIMIT $limit
        """
        rows = self.client.run_query(q, {"limit": limit}, write=False)
        out = []
        for r in rows:
            d = r
            out.append({
                "elementId": d.get("elementId"),
                "id": d.get("id"),
                "url": d.get("url"),
                "structural": d.get("structural"),
                "text": d.get("text"),
                "title": d.get("title"),
                "image": d.get("image"),
            })
        return out

    def _compute_scores(self,
                        user_text: Optional[List[float]],
                        user_struct: Optional[List[float]],
                        candidates: List[Dict[str, Any]],
                        weight_struct: float = 0.5) -> List[Tuple[Dict[str, Any], float]]:
        """
        weight_struct: вага структурної частини в сумарному скорі (0..1)
        Повертає список (candidate, combined_score)
        """
        text_embs = []
        struct_embs = []
        for c in candidates:
            text_embs.append(c.get("text") or [])
            struct_embs.append(c.get("structural") or [])

        # compute per-modality similarities
        text_scores = []
        struct_scores = []

        if user_text and any(text_embs):
            if np is not None:
                U = np.array(_l2_normalize(user_text), dtype=float)
                C = np.array([_l2_normalize(e) for e in text_embs], dtype=float)
                # align dims if needed
                try:
                    dots = C.dot(U)
                    # avoid division by zero because normalized vectors
                    text_scores = [float(x) for x in dots]
                except Exception:
                    text_scores = _cosine_scores_py(user_text, text_embs)
            else:
                text_scores = _cosine_scores_py(user_text, text_embs)
        else:
            text_scores = [0.0] * len(candidates)

        if user_struct and any(struct_embs):
            if np is not None:
                U = np.array(_l2_normalize(user_struct), dtype=float)
                C = np.array([_l2_normalize(e) for e in struct_embs], dtype=float)
                try:
                    dots = C.dot(U)
                    struct_scores = [float(x) for x in dots]
                except Exception:
                    struct_scores = _cosine_scores_py(user_struct, struct_embs)
            else:
                struct_scores = _cosine_scores_py(user_struct, struct_embs)
        else:
            struct_scores = [0.0] * len(candidates)

        # combine per-candidate with weights; if one modality missing, reduce to the other
        combined = []
        for c, ts, ss in zip(candidates, text_scores, struct_scores):
            # if both zero, score 0
            if (user_text is None or sum(abs(x) for x in (user_text or [])) == 0) and \
               (user_struct is None or sum(abs(x) for x in (user_struct or [])) == 0):
                score = 0.0
            elif user_text is None or all(v == 0.0 for v in text_scores):
                score = ss  # only structural
            elif user_struct is None or all(v == 0.0 for v in struct_scores):
                score = ts  # only text
            else:
                score = float(weight_struct) * ss + float(1.0 - weight_struct) * ts
            combined.append((c, score))
        return combined

    def recommend_top_n(self,
                        user_id: str,
                        n: int = 10,
                        candidate_limit: int = 2000,
                        weight_struct: float = 0.5) -> List[Dict[str, Any]]:
        """
        Основний метод: повертає top-n рекомендацій для user_id.
        Повертається список словників: {id, elementId, url, title, image, score}
        """
        user = self._fetch_user_embeddings(user_id)
        user_text = user.get("text")
        user_struct = user.get("structural")

        if (not user_text) and (not user_struct):
            return []

        candidates = self._fetch_page_candidates(limit=candidate_limit)
        if not candidates:
            return []

        scored = self._compute_scores(user_text, user_struct, candidates, weight_struct=weight_struct)
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:n]
        return [
            {
                "id": c.get("id"),
                "elementId": c.get("elementId"),
                "url": c.get("url"),
                "title": c.get("title"),
                "image": c.get("image"),
                "score": float(score)
            } for c, score in top
        ]


# приклад використання:
# svc = RecommendationService()
# cards = svc.recommend_top_n(user_id="user-123", n=10, weight_struct=0.6)