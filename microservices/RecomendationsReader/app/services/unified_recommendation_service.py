import logging
from fastapi import APIRouter, Query, Depends, BackgroundTasks
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
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
                "type": rec_type,
                "visit_count": node_data.get("visit_count", 0),
                "last_visited": node_data.get("last_visited")
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
        
        WHERE NOT EXISTS {{
            MATCH (u:User {{id: $user_id}})-[v:VISIT]->(page)
        }}

        OPTIONAL MATCH (page)<-[all_v:VISIT]-()

        RETURN 
            elementId(page) as elementId,
            page.url as url,
            page.title as title,
            page.image as image,
            score,
            count(all_v) as visit_count,
            // Збираємо всі мітки часу (з розширення та бекенду), щоб знайти макс. у Python
            collect(coalesce(all_v.last_visited, all_v.visitedAt)) as visit_times
        """
        try:
            results = self.client.run_query(query, {"user_id": user_id, "embedding": embedding, "k": k})
            
            parsed_results = []
            for r in results:
                # Безпечно шукаємо найновішу дату візиту
                latest_time = ""
                for t in r.get("visit_times", []):
                    time_str = str(t[-1]) if isinstance(t, list) and t else str(t) if t else ""
                    if time_str > latest_time and time_str != "None":
                        latest_time = time_str
                        
                parsed_results.append({
                    "id": r.get("elementId"),
                    "url": r.get("url"),
                    "title": r.get("title"),
                    "image": r.get("image"),
                    "score": r.get("score", 0.0),
                    "visit_count": r.get("visit_count", 0),
                    "last_visited": latest_time if latest_time else None
                })
            return parsed_results
            
        except Exception as e:
            log.error(f"Vector search failed on {index_name}: {e}")
            return []

    def _get_trending_fallback(self, page: int, size: int) -> Tuple[List[Dict[str, Any]], int]:
        # Витягуємо дані без фільтрації дат у Cypher, щоб уникнути конфліктів типів
        query = """
        MATCH (p:Page)<-[v:VISIT]-()
        RETURN 
            elementId(p) as id, 
            p.url as url, 
            p.title as title, 
            p.image as image, 
            collect(coalesce(v.last_visited, v.visitedAt)) as visit_times
        """
        results = self.client.run_query(query)
        
        # Обчислюємо дату відсічення (7 днів тому)
        cutoff_str = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        
        trending_data = []
        for r in results:
            valid_visits = 0
            latest_time = ""
            
            for t in r.get("visit_times", []):
                # Парсимо дату (розширення передає рядок, бекенд міг масив)
                time_str = str(t[-1]) if isinstance(t, list) and t else str(t) if t else ""
                if not time_str or time_str == "None":
                    continue
                    
                # Якщо візит відбувся в останні 7 днів
                if time_str[:19] >= cutoff_str[:19]:
                    valid_visits += 1
                    
                if time_str > latest_time:
                    latest_time = time_str
                    
            if valid_visits > 0:
                trending_data.append({
                    "id": r["id"], 
                    "url": r["url"], 
                    "title": r["title"], 
                    "image": r["image"], 
                    "score": valid_visits, # Score для трендів = кількість свіжих візитів
                    "type": "trending",
                    "visit_count": len(r["visit_times"]), # Глобальна статистика за весь час
                    "last_visited": latest_time if latest_time else None
                })
                
        # Сортуємо від найпопулярніших до найменш популярних
        trending_data.sort(key=lambda x: x["score"], reverse=True)
        total_count = len(trending_data)

        skip = (page - 1) * size
        return trending_data[skip : skip + size], total_count

    def track_user_visit(self, user_id: str, page_id: str, source: str = "recommendation") -> bool:
        # Безпечний запис: ми просто встановлюємо last_visited рядком і не чіпаємо масиви
        query = """
        MATCH (u:User {id: $user_id})
        MATCH (p:Page) WHERE elementId(p) = $page_id
        MERGE (u)-[v:VISIT]->(p)
        SET v.source = $source,
            v.last_visited = toString(datetime()),
            v.active_time = coalesce(v.active_time, 0.5)
        RETURN elementId(v) as visit_id
        """
        try:
            res = self.client.run_query(query, {"user_id": user_id, "page_id": page_id, "source": source})
            return bool(res)
        except Exception as e:
            log.error(f"Failed to track visit for user {user_id}: {e}")
            return False