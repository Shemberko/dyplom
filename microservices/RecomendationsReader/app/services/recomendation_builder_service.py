import os
import math
from typing import List, Dict, Optional, Any, Tuple
import logging

try:
    import numpy as np
except ImportError:
    np = None

from services.neo4j.query_runner import query_runner as neo4j_client

log = logging.getLogger(__name__)

# --- Внутрішні функції для обчислення косинусної подібності ---

def _l2_normalize(vec: List[float]) -> List[float]:
    """Нормалізація L2-нормою (довжиною) вектора."""
    v = [float(x) for x in vec]
    norm_sq = sum(x * x for x in v)
    norm = math.sqrt(norm_sq)
    return [x / norm for x in v] if norm > 1e-6 else [0.0] * len(v)


def _cosine_scores_py(query: List[float], candidates: List[List[float]]) -> List[float]:
    """
    Обчислює косинусну подібність між вектором запиту та списком векторів-кандидатів 
    за допомогою чистого Python (fallback, якщо немає NumPy).
    """
    qn = math.sqrt(sum(x * x for x in query))
    if qn == 0:
        return [0.0] * len(candidates)

    out = []
    for c in candidates:
        if not c:
            out.append(0.0)
            continue
            
        v = [float(x) for x in c]
        vn = math.sqrt(sum(x * x for x in v))
        
        if vn == 0:
             out.append(0.0)
             continue

        m = min(len(query), len(v))
        # Скалярний добуток
        dot = sum(query[i] * v[i] for i in range(m))
        out.append(dot / (qn * vn))
    return out


class RecommendationService:
    """
    Рекомендаційний сервіс: комбінує text & structural embeddings і повертає top-N сторінок.
    """

    def __init__(self, client: Any = None):
        # Якщо клієнт не переданий, використовуємо модуль-рівневий екземпляр
        self.client = client or neo4j_client

    def _fetch_user_embeddings(self, user_id: str) -> Dict[str, Optional[List[float]]]:
        """Отримує обидва типи ембедінгів для користувача з Neo4j, використовуючи COALESCE."""
        # [ПОКРАЩЕНО] Використовуємо COALESCE для надійності в обох полях
        q = """
        MATCH (u:User {id: $user_id})
        RETURN u.textEmbedding AS text_emb, 
               u.structuralEmbedding AS struct_emb
        """
        row = self.client.run_one(q, {"user_id": user_id}, write=False)
        if not row:
            log.warning(f"User {user_id} not found or has no embeddings.")
            return {"text": None, "structural": None}
        return {"text": row.get("text_emb"), "structural": row.get("struct_emb")}

    def _fetch_page_candidates(self, user_id: str, limit: int = 2000) -> List[Dict[str, Any]]:
        """
        Отримує сторінки-кандидати, які користувач ще не відвідав, 
        з наявними ембедінгами.
        """
        # [ПОКРАЩЕНО] Використовуємо COALESCE для полів Page також
        q = """
        MATCH (p:Page)
        WHERE NOT EXISTS { (u:User {id: $user_id})-[:VISIT]->(p) }
        AND (p.structuralEmbedding IS NOT NULL)
             OR (p.text_embedding IS NOT NULL)
        
        RETURN elementId(p) AS elementId, p.id AS id, p.url AS url, p.title AS title, 
               p.structuralEmbedding AS structural, 
               p.text_embedding AS text
        LIMIT $limit
        """
        
        rows = self.client.run_query(q, {"limit": limit, "user_id": user_id}, write=False)
        
        out = []
        for r in rows:
             out.append({
                "elementId": r.get("elementId"),
                "id": r.get("id"),
                "url": r.get("url"),
                "title": r.get("title"),
                "image": r.get("image"),
                "structural": r.get("structural"),
                "text": r.get("text"),
            })
        return out

    def _compute_scores(self,
                        user_text: Optional[List[float]],
                        user_struct: Optional[List[float]],
                        candidates: List[Dict[str, Any]],
                        weight_struct: float = 0.5) -> List[Tuple[Dict[str, Any], float, float, float]]:
        """
        Обчислює косинусну подібність для кожної модальності та об'єднує їх.
        Повертає список (candidate, combined_score, text_score, struct_score).
        """
        
        # 1. Підготовка вхідних даних
        text_embs = [c.get("text") or [] for c in candidates]
        struct_embs = [c.get("structural") or [] for c in candidates]
        
        # 2. Обчислення текстових скорів
        if user_text:
            if np is not None:
                try:
                    U = np.array(_l2_normalize(user_text), dtype=float)
                    C = np.array([_l2_normalize(e) for e in text_embs], dtype=float)
                    text_scores = [float(x) for x in C.dot(U)]
                except Exception:
                    text_scores = _cosine_scores_py(user_text, text_embs)
            else:
                text_scores = _cosine_scores_py(user_text, text_embs)
        else:
            text_scores = [0.0] * len(candidates)
        
        # 3. Обчислення структурних скорів (аналогічно)
        if user_struct:
            if np is not None:
                try:
                    U = np.array(_l2_normalize(user_struct), dtype=float)
                    C = np.array([_l2_normalize(e) for e in struct_embs], dtype=float)
                    struct_scores = [float(x) for x in C.dot(U)]
                except Exception:
                    struct_scores = _cosine_scores_py(user_struct, struct_embs)
            else:
                struct_scores = _cosine_scores_py(user_struct, struct_embs)
        else:
            struct_scores = [0.0] * len(candidates)

        # 4. Комбінування скорів (Гібридний Скоринг)
        combined = []
        weight_text = 1.0 - weight_struct
        
        for c, ts, ss in zip(candidates, text_scores, struct_scores):
            score = 0.0
            
            # Логіка для випадку, коли одна з модальностей відсутня:
            is_text_valid = (user_text is not None) and (ts != 0.0)
            is_struct_valid = (user_struct is not None) and (ss != 0.0)
            
            if is_text_valid and is_struct_valid:
                # Обидва вектори присутні
                score = weight_struct * ss + weight_text * ts
            elif is_text_valid:
                # Тільки текстовий вектор
                score = ts
            elif is_struct_valid:
                # Тільки структурний вектор
                score = ss
            
            # [ЗМІНА] Повертаємо всі три скори
            combined.append((c, score, ts, ss))
            
        return combined

    def recommend_top_n(self,
                        user_id: str,
                        n: int = 10,
                        candidate_limit: int = 2000,
                        weight_struct: float = 0.5) -> List[Dict[str, Any]]:
        """
        Основний метод: повертає top-n рекомендацій для user_id.
        Повертається список словників: {id, elementId, url, title, score, text_score, struct_score}
        """
        
        # 1. Отримати вектори користувача
        user = self._fetch_user_embeddings(user_id)
        user_text = user.get("text")
        user_struct = user.get("structural")

        if (not user_text) and (not user_struct):
            log.info(f"Cannot recommend for user {user_id}: no embeddings found.")
            return []

        # 2. Отримати сторінки-кандидати (виключаючи вже відвідані)
        candidates = self._fetch_page_candidates(user_id, limit=candidate_limit)
        if not candidates:
            log.info("No valid page candidates found.")
            return []

        # 3. Обчислити та відсортувати скори
        scored = self._compute_scores(user_text, user_struct, candidates, weight_struct=weight_struct)
        
        # Сортування виконується за другим елементом у кортежі (combined_score)
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # 4. Повернути top-N
        top = scored[:n]
        return [
            {
                "id": c.get("id"),
                "elementId": c.get("elementId"),
                "url": c.get("url"),
                "title": c.get("title"),
                "image": c.get("image"),
                "score": float(score),
                "text_score": float(ts),      # НОВЕ: Окремий текстовий скор
                "struct_score": float(ss)     # НОВЕ: Окремий структурний скор
            } for c, score, ts, ss in top
        ]