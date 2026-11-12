import logging
from typing import Dict, Any
from app.services.neo4j.query_runner import query_runner as neo4j_client

log = logging.getLogger(__name__)

class StatsService:
    def __init__(self, client: Any = None):
        self.client = client or neo4j_client

    def get_platform_stats(self) -> Dict[str, int]:
        """
        Повертає загальну кількість користувачів та проаналізованих сторінок.
        Використовує підзапити CALL для максимальної швидкодії (читання з count store).
        """
        query = """
        CALL { MATCH (u:User) RETURN count(u) AS users }
        CALL { MATCH (p:Page) RETURN count(p) AS pages }
        RETURN users AS total_users, pages AS total_pages
        """
        
        try:
            res = self.client.run_one(query)
            if res:
                return {
                    "total_users": res.get("total_users", 0),
                    "total_pages": res.get("total_pages", 0)
                }
            return {"total_users": 0, "total_pages": 0}
            
        except Exception as e:
            log.error(f"Failed to fetch platform stats: {e}")
            return {"total_users": 0, "total_pages": 0}