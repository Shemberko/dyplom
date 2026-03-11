import logging
from fastapi import APIRouter, Query, Depends, BackgroundTasks
from typing import List, Dict, Any, Optional, Tuple
from app.dependencies.auth import get_current_user_id
from app.services.neo4j.query_runner import query_runner as neo4j_client

log = logging.getLogger(__name__)
router = APIRouter()

class UnifiedRecommendationService:
    """
    Уніфікований сервіс рекомендацій.
    Об'єднує результати текстового (Content-Based) та гібридного (GraphSAGE) підходів.
    """
    def __init__(self, client: Any = None):
        self.client = client or neo4j_client

    def get_recommendations(self, user_id: str, page: int, size: int, weight_struct: float) -> Tuple[List[Dict[str, Any]], int]:
        """
        Повертає зріз рекомендацій (data) та загальну кількість знайдених кандидатів (total_count).
        """
        user_profile = self._fetch_user_profiles(user_id)
        
        text_emb = user_profile.get("text_emb")
        hybrid_emb = user_profile.get("hybrid_emb")

        if not text_emb and not hybrid_emb:
            log.info(f"User {user_id} has no embeddings. Falling back to trending.")
            return self._get_trending_fallback(page, size)

        limit_needed = page * size
        fetch_k = limit_needed * 3

        text_recs = {}
        if text_emb and weight_struct < 1.0:
            text_recs = {r['id']: r for r in self._vector_search('page_text_index', user_id, text_emb, fetch_k)}

        hybrid_recs = {}
        if hybrid_emb and weight_struct > 0.0:
            hybrid_recs = {r['id']: r for r in self._vector_search('page_hybrid_index', user_id, hybrid_emb, fetch_k)}

        all_ids = set(text_recs.keys()).union(set(hybrid_recs.keys()))
        merged_results = []

        for pid in all_ids:
            t_score = text_recs[pid]['score'] if pid in text_recs else 0.0
            h_score = hybrid_recs[pid]['score'] if pid in hybrid_recs else 0.0

            t_contrib = t_score * (1.0 - weight_struct)
            h_contrib = h_score * weight_struct
            final_score = t_contrib + h_contrib
            
            if final_score < 0.1:
                continue

            if pid in text_recs and pid in hybrid_recs:
                if abs(h_score - t_score) <= 0.03:
                    rec_type = "mixed"
                elif h_score > t_score:
                    rec_type = "hybrid"
                else:
                    rec_type = "text"
            elif pid in text_recs:
                rec_type = "text"
            else:
                rec_type = "hybrid"

            node_data = text_recs.get(pid) or hybrid_recs.get(pid)

            merged_results.append({
                "id": pid,
                "url": node_data["url"],
                "title": node_data["title"],
                "image": node_data["image"],
                "score": round(final_score, 4),
                "text_score": round(t_score, 4),
                "hybrid_score": round(h_score, 4),
                "type": rec_type
            })
        merged_results.sort(key=lambda x: x['score'], reverse=True)
        total_count = len(merged_results)

        start_idx = (page - 1) * size
        end_idx = start_idx + size
        
        return merged_results[start_idx:end_idx], total_count

    def _fetch_user_profiles(self, user_id: str) -> Dict[str, Any]:
        query = """
        MATCH (u:User {id: $user_id})
        RETURN u.text_embedding AS text_emb, u.hybridEmbedding AS hybrid_emb
        """
        res = self.client.run_one(query, {"user_id": user_id})
        return res if res else {}

    def _vector_search(self, index_name: str, user_id: str, embedding: List[float], k: int) -> List[Dict[str, Any]]:
        query = f"""
        CALL db.index.vector.queryNodes('{index_name}', $k, $embedding)
        YIELD node AS page, score
        
        // Повністю виключаємо відвідані сторінки
        WHERE NOT EXISTS {{
            MATCH (u:User {{id: $user_id}})-[v:VISIT]->(page)
        }}

        RETURN 
            elementId(page) as elementId,
            page.url as url,
            page.title as title,
            page.image as image,
            score
        """
        try:
            results = self.client.run_query(query, {"user_id": user_id, "embedding": embedding, "k": k})
            return [{
                "id": r.get("elementId"),
                "url": r.get("url"),
                "title": r.get("title"),
                "image": r.get("image"),
                "score": r.get("score", 0.0)
            } for r in results]
        except Exception as e:
            log.error(f"Vector search failed on {index_name}: {e}")
            return []

    def _get_trending_fallback(self, page: int, size: int) -> Tuple[List[Dict[str, Any]], int]:
        count_query = """
        MATCH (p:Page)<-[v:VISIT]-()
        WHERE datetime(v.visitedAt[-1]) > datetime() - duration('P7D')
        RETURN count(DISTINCT p) as total
        """
        total_res = self.client.run_one(count_query)
        total_count = total_res["total"] if total_res else 0

        skip = (page - 1) * size
        query = """
        MATCH (p:Page)<-[v:VISIT]-()
        WHERE datetime(v.visitedAt[-1]) > datetime() - duration('P7D')
        RETURN elementId(p) as id, p.url as url, p.title as title, p.image as image, count(v) as score
        ORDER BY score DESC
        SKIP $skip LIMIT $limit
        """
        results = self.client.run_query(query, {"skip": skip, "limit": size})
        
        data = [{
            "id": r["id"], "url": r["url"], "title": r["title"], 
            "image": r["image"], "score": r["score"], "type": "trending"
        } for r in results]
        
        return data, total_count

    def track_user_visit(self, user_id: str, page_id: str, source: str = "recommendation") -> bool:
        query = """
        MATCH (u:User {id: $user_id})
        MATCH (p:Page) WHERE elementId(p) = $page_id
        MERGE (u)-[v:VISIT]->(p)
        SET v.visitedAt = coalesce(v.visitedAt, []) + datetime(),
            v.source = $source,
            v.last_visited = datetime(),
            v.active_time = coalesce(v.active_time, 0.5)
        RETURN elementId(v) as visit_id
        """
        try:
            res = self.client.run_query(query, {"user_id": user_id, "page_id": page_id, "source": source})
            return bool(res)
        except Exception as e:
            log.error(f"Failed to track visit for user {user_id}: {e}")
            return False