import os
import logging
import traceback
from neo4j import Driver
from typing import Any, Dict, List, Optional
from .base_service import BaseService


log = logging.getLogger(__name__)

class QueryRunner(BaseService):
    """
    Розширює BaseService, щоб надати допоміжні методи.
    Успадковує 'self.driver' від BaseService.
    """
    def __init__(self) -> None:
        super().__init__()

    def run_query(self, cypher: str, params: Optional[Dict[str, Any]] = None, write: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Виконує cypher-запит і повертає список рядків (кожен як dict).
        """
        if not self._driver:
            log.error("Neo4j driver не ініціалізовано.")
            raise Exception("Neo4j driver не ініціалізовано.")
        
        try:
            records, _, _ = self._driver.execute_query(
                cypher,
                params or {},
                database_=os.getenv("NEO4J_DATABASE", "neo4j")
            )
            return [dict(record) for record in records]
        except Exception as e:
            log.exception(f"Neo4j query failed: {cypher}")
            raise

    def run_one(self, cypher: str, params: Optional[Dict[str, Any]] = None, write: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        """
        Виконує запит і повертає перший рядок як dict або None.
        """
        rows = self.run_query(cypher, params, write)
        return rows[0] if rows else None

    def run_single_value(self, cypher: str, params: Optional[Dict[str, Any]] = None, key: Optional[str] = None, write: Optional[bool] = None) -> Any:
        """
        Виконує запит і повертає єдине скалярне значення.
        """
        row = self.run_one(cypher, params, write)
        if not row:
            return None
        if key:
            return row.get(key)
        try:
            return next(iter(row.values()))
        except StopIteration:
            return None

    def graph_exists(self, graph_name: str) -> bool:
        """
        Перевіряє існування GDS проєкції графа.
        """
        q = "CALL gds.graph.exists($name) YIELD exists RETURN exists"
        res = self.run_one(q, {"name": graph_name}, write=False)
        if res is None:
            return False
        return bool(res.get("exists") or res.get("value") or False)

    def drop_graph_if_exists(self, graph_name: str) -> None:
        """
        Видаляє GDS проєкцію графа; ігнорує, якщо її не існує.
        """
        try:
            self.run_query(f"CALL gds.graph.drop('{graph_name}')")
        except Exception:
            log.debug("graph drop ignored or failed for %s", graph_name, exc_info=True)


query_runner = QueryRunner()