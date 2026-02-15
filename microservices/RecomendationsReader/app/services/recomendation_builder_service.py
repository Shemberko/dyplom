# CREATE VECTOR INDEX page_hybrid_index IF NOT EXISTS
# FOR (p:Page)
# ON (p.hybridEmbedding)
# OPTIONS {indexConfig: {
#  `vector.dimensions`: 128,
#  `vector.similarity_function`: 'cosine'
# }}


import logging
from typing import List, Dict, Any, Optional
from app.services.neo4j.query_runner import query_runner as neo4j_client

log = logging.getLogger(__name__)

class RecommendationService:
    def __init__(self, client: Any = None):
        self.client = client or neo4j_client

    def recommend_top_n(self, user_id: str, n: int = 10) -> List[Dict[str, Any]]:
        """
        Повертає top-n рекомендацій, використовуючи Neo4j Vector Index.
        Фільтрує сторінки, які користувач відвідував за останні 30 днів.
        """
        
        user_emb = self._fetch_user_embedding(user_id)
        
        if not user_emb:
            log.info(f"User {user_id} has no profile. Falling back to trending.")
            return self._get_trending_fallback(n)

        return self._vector_search(user_id, user_emb, n)

    def _fetch_user_embedding(self, user_id: str) -> Optional[List[float]]:
        query = """
        MATCH (u:User {id: $user_id})
        RETURN u.hybridEmbedding AS emb
        """
        res = self.client.run_one(query, {"user_id": user_id})
        return res.get("emb") if res else None

    def _vector_search(self, user_id: str, embedding: List[float], n: int) -> List[Dict[str, Any]]:
        """
        Використовує db.index.vector.queryNodes для пошуку.
        Повністю виключає сторінки, які користувач коли-небудь відвідував.
        """
        candidates_to_fetch = n * 10 
        
        query = """
        CALL db.index.vector.queryNodes('page_hybrid_index', $k, $embedding)
        YIELD node AS page, score
        
        // Використовуємо NOT EXISTS для повної фільтрації відвіданих сторінок
        WHERE NOT EXISTS {
            MATCH (u:User {id: $user_id})-[v:VISIT]->(page)
        }

        RETURN 
            elementId(page) as elementId,
            page.url as url,
            page.title as title,
            page.image as image,
            score
        ORDER BY score DESC
        LIMIT $limit
        """
        
        try:
            results = self.client.run_query(query, {
                "user_id": user_id,
                "embedding": embedding,
                "k": candidates_to_fetch,
                "limit": n
            })
            
            return [{
                "id": r.get("elementId"),
                "url": r.get("url"),
                "title": r.get("title"),
                "image": r.get("image"),
                "score": round(r.get("score", 0.0), 4)
            } for r in results]

        except Exception as e:
            log.error(f"Vector search failed: {e}")
            return []

    def _get_trending_fallback(self, n: int) -> List[Dict[str, Any]]:
        """
        Повертає популярні сторінки, якщо у юзера ще немає профілю.
        Наприклад, сторінки з найбільшою кількістю візитів за 24 години.
        """
        query = """
        MATCH (p:Page)<-[v:VISIT]-()
        WHERE datetime(v.visitedAt[-1]) > datetime() - duration('P1D')
        RETURN p.url as url, p.title as title, p.image as image, count(v) as visits
        ORDER BY visits DESC
        LIMIT $limit
        """
        results = self.client.run_query(query, {"limit": n})
        return [
            {
                "url": r["url"], 
                "title": r["title"], 
                "image": r["image"], 
                "score": 0.0
            } for r in results
        ]