import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.neo4j.query_runner import query_runner as neo4j_client

log = logging.getLogger(__name__)

class UserStatisticService:
    def __init__(self, client: Any = None):
        self.client = client or neo4j_client

    def get_user_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """
        Збирає повний пакет даних для фронтенд-дашборду.
        """
        try:
            # Виправлено f-стрінгу для виводу в консоль
            print(f"Statistic for user: {user_id}")

            return {
                "summary": self._get_general_summary(user_id),
                "top_categories": self._get_top_categories(user_id),
                "activity_chart": self._get_activity_by_day(user_id),
                "browsing_habits": self._get_browsing_time_stats(user_id)
            }
        except Exception as e:
            log.error(f"Failed to fetch stats for user {user_id}: {e}")
            return {}

    def _get_general_summary(self, user_id: str) -> Dict[str, Any]:
        """Загальні цифри: скільки всього сторінок відвідано, унікальних сайтів тощо."""
        # Замість APOC використовуємо OPTIONAL MATCH та count(DISTINCT)
        query = """
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (u)-[v:VISIT]->(p:Page)
        OPTIONAL MATCH (p)-[:IN_CATEGORY]->(c:Category)
        RETURN 
            count(v) as total_visits,
            count(DISTINCT p) as unique_pages,
            count(DISTINCT c) as total_categories
        """
        return self.client.run_one(query, {"user_id": user_id})

    def _get_top_categories(self, user_id: str) -> List[Dict[str, Any]]:
        """Дані для Pie Chart (Кругової діаграми) за інтересами."""
        query = """
        MATCH (u:User {id: $user_id})-[v:VISIT]->(p:Page)-[:IN_CATEGORY]->(c:Category)
        RETURN c.name as name, count(v) as value
        ORDER BY value DESC
        LIMIT 5
        """
        return self.client.run_query(query, {"user_id": user_id})

    def _get_activity_by_day(self, user_id: str) -> List[Dict[str, Any]]:
        """Дані для Line Chart (Графіка активності) за останній тиждень."""
        query = """
        MATCH (u:User {id: $user_id})-[v:VISIT]->(:Page)
        UNWIND v.visitedAt AS visitTime
        WITH datetime(visitTime) AS dt
        WHERE dt > datetime() - duration('P7D')
        RETURN toString(date(dt)) AS date, count(*) AS count
        ORDER BY date ASC
        """
        return self.client.run_query(query, {"user_id": user_id})

    def _get_browsing_time_stats(self, user_id: str) -> List[Dict[str, Any]]:
        """Розподіл активності по годинах доби."""
        query = """
        MATCH (u:User {id: $user_id})-[v:VISIT]->(:Page)
        UNWIND v.visitedAt AS visitTime
        WITH datetime(visitTime).hour AS hour
        RETURN hour, count(*) AS count
        ORDER BY hour
        """
        return self.client.run_query(query, {"user_id": user_id})