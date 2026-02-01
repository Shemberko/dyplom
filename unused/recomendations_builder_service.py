# import math
# import logging
# from typing import List, Dict, Optional, Any, Tuple

# # Спроба імпорту NumPy для оптимізації
# try:
#     import numpy as np
# except ImportError:
#     np = None

# # Імпорт клієнта Neo4j
# from app.services.neo4j.query_runner import query_runner as neo4j_client

# log = logging.getLogger(__name__)

# def _l2_normalize(vec: List[float]) -> List[float]:
#     """Нормалізація L2-нормою (довжиною) вектора."""
#     v = [float(x) for x in vec]
#     norm_sq = sum(x * x for x in v)
#     norm = math.sqrt(norm_sq)
#     return [x / norm for x in v] if norm > 1e-6 else [0.0] * len(v)

# def _cosine_scores_py(query: List[float], candidates: List[List[float]]) -> List[float]:
#     """
#     Обчислює косинусну подібність між вектором запиту та списком векторів-кандидатів 
#     за допомогою чистого Python (fallback).
#     """
#     qn = math.sqrt(sum(x * x for x in query))
#     if qn == 0:
#         return [0.0] * len(candidates)

#     out = []
#     for c in candidates:
#         if not c:
#             out.append(0.0)
#             continue
            
#         v = [float(x) for x in c]
#         vn = math.sqrt(sum(x * x for x in v))
        
#         if vn == 0:
#              out.append(0.0)
#              continue

#         m = min(len(query), len(v))
#         dot = sum(query[i] * v[i] for i in range(m))
#         out.append(dot / (qn * vn))
#     return out


# class RecommendationService:
#     """
#     Рекомендаційний сервіс: використовує гібридні ембедінги (GraphSAGE)
#     для пошуку найбільш релевантних сторінок.
#     """

#     def __init__(self, client: Any = None):
#         self.client = client or neo4j_client

#     def _fetch_user_embedding(self, user_id: str) -> Optional[List[float]]:
#         """
#         Отримує гібридний ембедінг користувача (u.hybridEmbedding).
#         """
#         q = """
#         MATCH (u:User {id: $user_id})
#         RETURN u.hybridEmbedding AS hybrid_emb
#         """
#         row = self.client.run_one(q, {"user_id": user_id}, write=False)
        
#         if not row or not row.get("hybrid_emb"):
#             log.warning(f"User {user_id} not found or has no hybrid embedding.")
#             return None
            
#         return row.get("hybrid_emb")

#     def _fetch_page_candidates(self, user_id: str, limit: int = 2000) -> List[Dict[str, Any]]:
#         """
#         Отримує сторінки-кандидати, які користувач ще не відвідав, 
#         з наявним гібридним ембедінгом.
#         """
#         q = """
#         MATCH (p:Page)
#         WHERE p.hybridEmbedding IS NOT NULL
#           AND NOT EXISTS { (u:User {id: $user_id})-[:VISIT]->(p) }
        
#         RETURN elementId(p) AS elementId, p.id AS id, p.url AS url, p.title AS title, p.image AS image,
#                p.hybridEmbedding AS embedding
#         LIMIT $limit
#         """
        
#         rows = self.client.run_query(q, {"limit": limit, "user_id": user_id}, write=False)
        
#         out = []
#         for r in rows:
#              out.append({
#                 "elementId": r.get("elementId"),
#                 "id": r.get("id"),
#                 "url": r.get("url"),
#                 "title": r.get("title"),
#                 "image": r.get("image"),
#                 "embedding": r.get("embedding"), # Гібридний вектор
#             })
#         return out

#     def _compute_scores(self,
#                         user_vec: List[float],
#                         candidates: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], float]]:
#         """
#         Обчислює косинусну подібність між вектором користувача та кандидатами.
#         Повертає список (candidate, score).
#         """
#         if not user_vec:
#             return [(c, 0.0) for c in candidates]

#         # Отримуємо список векторів кандидатів
#         cand_vecs = [c.get("embedding") or [] for c in candidates]
        
#         scores = []
        
#         # 1. Спроба використати NumPy (швидко)
#         if np is not None:
#             try:
#                 U = np.array(_l2_normalize(user_vec), dtype=float)
#                 # Нормалізуємо вектори кандидатів
#                 C_list = [_l2_normalize(v) for v in cand_vecs]
                
#                 # Перевірка на порожні списки (щоб уникнути помилок створення np.array)
#                 if not C_list or len(C_list[0]) != len(U):
#                     # Fallback якщо розмірності не співпадають або список порожній
#                     scores = _cosine_scores_py(user_vec, cand_vecs)
#                 else:
#                     C = np.array(C_list, dtype=float)
#                     scores = [float(x) for x in C.dot(U)]
#             except Exception as e:
#                 log.error(f"NumPy error: {e}. Falling back to pure Python.")
#                 scores = _cosine_scores_py(user_vec, cand_vecs)
        
#         # 2. Fallback на чистий Python (повільніше)
#         else:
#             scores = _cosine_scores_py(user_vec, cand_vecs)
            
#         # Об'єднуємо кандидата з його оцінкою
#         return list(zip(candidates, scores))

#     def recommend_top_n(self,
#                         user_id: str,
#                         n: int = 10,
#                         candidate_limit: int = 2000) -> List[Dict[str, Any]]:
#         """
#         Основний метод: повертає top-n рекомендацій для user_id на основі GraphSAGE Hybrid Embeddings.
#         """
        
#         # 1. Отримати вектор користувача
#         user_emb = self._fetch_user_embedding(user_id)
#         if not user_emb:
#             log.info(f"Cannot recommend for user {user_id}: no hybrid embedding found.")
#             return []

#         # 2. Отримати кандидатів
#         candidates = self._fetch_page_candidates(user_id, limit=candidate_limit)
#         if not candidates:
#             log.info("No valid page candidates found.")
#             return []

#         # 3. Обчислити скори
#         scored = self._compute_scores(user_emb, candidates)
        
#         # 4. Відсортувати за спаданням скору
#         scored.sort(key=lambda x: x[1], reverse=True)
        
#         # 5. Форматувати результат
#         top = scored[:n]
#         return [
#             {
#                 "id": c.get("id"),
#                 "elementId": c.get("elementId"),
#                 "url": c.get("url"),
#                 "title": c.get("title"),
#                 "image": c.get("image"),
#                 "score": float(score)
#             } for c, score in top
#         ]

