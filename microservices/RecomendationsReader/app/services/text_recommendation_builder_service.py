# CREATE VECTOR INDEX page_text_index IF NOT EXISTS
# FOR (p:Page)
# ON (p.text_embedding)
# OPTIONS {indexConfig: {
#  `vector.dimensions`: 384,
#  `vector.similarity_function`: 'cosine'
# }}

import logging
from typing import List, Dict, Any, Optional
from app.services.neo4j.query_runner import query_runner as neo4j_client

log = logging.getLogger(__name__)

class TextRecommendationBuilderService:
    """
    Сервіс контентних рекомендацій (Content-Based).
    Шукає схожі статті на основі text_embedding останньої відвіданої сторінки користувача.
    """
    def __init__(self, client: Any = None):
        self.client = client or neo4j_client

    def recommend_top_n(self, user_id: str, n: int = 10) -> List[Dict[str, Any]]:
        """
        Повертає top-n рекомендацій за текстовою схожістю до останнього інтересу юзера.
        """
        
        target_emb = self._fetch_latest_interaction_embedding(user_id)
        
        if not target_emb:
            log.info(f"User {user_id} has no valid recent history. Falling back to trending.")
            return self._get_trending_fallback(n)

        return self._vector_search(user_id, target_emb, n)

    def _fetch_latest_interaction_embedding(self, user_id: str) -> Optional[List[float]]:
        """
        Знаходить останню відвідану сторінку, яка має text_embedding,
        щоб на її основі шукати схожий контент.
        """
        query = """
        MATCH (u:User {id: $user_id})-[v:VISIT]->(p:Page)
        WHERE p.text_embedding IS NOT NULL
          AND v.visitedAt IS NOT NULL
        RETURN p.text_embedding AS emb
        // Сортуємо за часом останнього візиту, щоб взяти найсвіжіший інтерес
        ORDER BY datetime(v.visitedAt[-1]) DESC
        LIMIT 1
        """
        res = self.client.run_one(query, {"user_id": user_id})
        return res.get("emb") if res else None

    def _vector_search(self, user_id: str, embedding: List[float], n: int) -> List[Dict[str, Any]]:
        """
        Шукає схожі за змістом (текстом) сторінки через page_text_index.
        """
        candidates_to_fetch = n * 5
        
        query = """
        // 1. Пошук за текстовим індексом
        CALL db.index.vector.queryNodes('page_text_index', $k, $embedding)
        YIELD node AS page, score
        
        // 2. Фільтрація переглянутого (як і раніше)
        OPTIONAL MATCH (u:User {id: $user_id})-[v:VISIT]->(page)
        WHERE v IS NULL 
           OR datetime(v.visitedAt[-1]) < datetime() - duration('P30D')
           
        RETURN 
            elementId(page) as elementId,
            page.url as url,
            page.title as title,
            page.image as image,
            score
        
        LIMIT $limit
        """
        
        try:
            results = self.client.run_query(query, {
                "user_id": user_id,
                "embedding": embedding,
                "k": candidates_to_fetch,
                "limit": n
            })
            
            recommendations = []
            for r in results:
                recommendations.append({
                    "id": r.get("elementId"),
                    "url": r.get("url"),
                    "title": r.get("title"),
                    "image": r.get("image"),
                    "score": round(r.get("score", 0.0), 4),
                    "type": "content-based"
                })
            
            return recommendations

        except Exception as e:
            log.error(f"Text vector search failed: {e}")
            return []

    def _get_trending_fallback(self, n: int) -> List[Dict[str, Any]]:
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
                "score": 0.0,
                "type": "trending"
            } for r in results
        ]