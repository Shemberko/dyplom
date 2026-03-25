import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from app.services.neo4j.query_runner import query_runner as neo4j_client

log = logging.getLogger(__name__)

class HistoryService:
    def __init__(self, client: Any = None):
        self.client = client or neo4j_client

    def get_user_history(self, user_id: str, n: int = 10, days_ago: int = 7) -> List[Dict[str, Any]]:
        """
        Повертає top-n останніх відвіданих сторінок користувача.
        Витягує дані з Neo4j, після чого безпечно парсить дати та сортує у Python,
        щоб уникнути конфліктів типів (рядок чи масив).
        """
        query = """
        MATCH (u:User {id: $user_id})-[v:VISIT]->(p:Page)
        // Шукаємо будь-яку мітку часу (і від Extension, і від Backend)
        WHERE v.last_visited IS NOT NULL OR v.visitedAt IS NOT NULL
        
        OPTIONAL MATCH (p)<-[all_v:VISIT]-()
        
        RETURN 
            elementId(p) as elementId,
            p.url as url,
            p.title as title,
            p.image as image,
            v.last_visited as last_visited,
            v.visitedAt as visitedAt,
            count(all_v) as visit_count
        """
        
        try:
            results = self.client.run_query(query, {"user_id": user_id})
            
            # Обчислюємо дату відсічення (N днів тому)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
            cutoff_str = cutoff_date.isoformat() # напр. '2026-03-15T12:00:00+00:00'
            
            history_list = []
            
            for r in results:
                # Беремо час візиту звідти, де він є
                time_val = r.get("last_visited") or r.get("visitedAt")
                
                # Розширення може писати рядок, а бекенд - масив. Обробляємо обидва варіанти:
                if isinstance(time_val, list):
                    if not time_val: continue
                    time_str = str(time_val[-1])
                else:
                    time_str = str(time_val)
                    
                if not time_str or time_str == "None":
                    continue
                    
                # Лексикографічне порівняння дат у форматі ISO (YYYY-MM-DDTHH:MM:SS)
                # Відкидаємо візити, старіші за days_ago
                if time_str[:19] < cutoff_str[:19]:
                    continue
                    
                history_list.append({
                    "id": r.get("elementId"),
                    "url": r.get("url"),
                    "title": r.get("title"),
                    "image": r.get("image"),
                    "last_visited": time_str,
                    "visit_count": r.get("visit_count") or 1
                })
                
            # Сортуємо у Python: від найновіших дат до найстаріших
            history_list.sort(key=lambda x: x["last_visited"], reverse=True)
            
            # Повертаємо потрібну кількість записів
            return history_list[:n]

        except Exception as e:
            log.error(f"Failed to fetch history for user {user_id}: {e}")
            return []

    def clear_user_history(self, user_id: str) -> bool:
        query = """
        MATCH (u:User {id: $user_id})
        SET u.text_embedding = null,
            u.sumWeightedTextEmbedding = null,
            u.totalWeight = 0.0,
            u.profileUpdatedAt = null
        WITH u
        OPTIONAL MATCH (u)-[v:VISIT]->(:Page)
        DELETE v
        """
        try:
            self.client.run_query(query, {"user_id": user_id})
            log.info(f"History and profile cleared for user {user_id}")
            return True
        except Exception as e:
            log.error(f"Failed to clear history for user {user_id}: {e}")
            return False
        
    def delete_visit(self, user_id: str, page_id: str) -> bool:
        query = """
        MATCH (u:User {id: $user_id})-[v:VISIT]->(p:Page)
        WHERE elementId(p) = $page_id
        
        WITH u, v, p,
             CASE WHEN v.tracked = true AND p.text_embedding IS NOT NULL AND u.sumWeightedTextEmbedding IS NOT NULL
                  THEN (coalesce(v.active_time, 0.5) * exp(-0.05 * duration.inDays(datetime(v.visitedAt[-1]), datetime()).days) * CASE WHEN v.source = 'recommendation' THEN 2.0 ELSE 1.0 END)
                  ELSE 0.0 END AS w
                  
        WITH u, v, p, w,
             CASE WHEN w > 0 THEN 
                 [i IN range(0, size(u.sumWeightedTextEmbedding)-1) | u.sumWeightedTextEmbedding[i] - (p.text_embedding[i] * w)]
             ELSE u.sumWeightedTextEmbedding END AS new_sum,
             CASE WHEN w > 0 THEN u.totalWeight - w ELSE u.totalWeight END AS new_total_w
             
        WITH u, v, p, w, new_sum, new_total_w,
             CASE WHEN w > 0 THEN sqrt(reduce(s = 0.0, x IN new_sum | s + x*x)) ELSE 1.0 END AS norm
             
        WITH u, v, p, w, new_sum, new_total_w, norm,
             CASE WHEN w > 0 AND norm > 0 THEN [x IN new_sum | x / norm] 
                  WHEN w > 0 AND norm = 0 THEN [x IN new_sum | 0.0]
                  ELSE u.text_embedding END AS new_normalized_emb
                  
        FOREACH (_ IN CASE WHEN w > 0 THEN [1] ELSE [] END |
            SET u.sumWeightedTextEmbedding = new_sum,
                u.totalWeight = new_total_w,
                u.text_embedding = new_normalized_emb
        )
        
        DELETE v
        RETURN true AS success
        """
        try:
            res = self.client.run_query(query, {"user_id": user_id, "page_id": page_id})
            if res:
                log.info(f"Visit removed for user {user_id}, page {page_id}. Profile updated: {bool(res[0]['success'])}")
                return True
            return False
        except Exception as e:
            log.error(f"Failed to remove visit for user {user_id} and page {page_id}: {e}")
            return False