import os
import logging
import traceback
from neo4j import Driver
from typing import Any, Dict, List, Optional

# [ВИПРАВЛЕНО 1] Абсолютний імпорт для BaseService
from .base_service import BaseService

# [ВИПРАВЛЕНО 2] Визначення логгера
log = logging.getLogger(__name__)

class QueryRunner(BaseService):
    """
    Розширює BaseService, щоб надати допоміжні методи.
    Успадковує 'self.driver' від BaseService.
    """

    # [ВИПРАВЛЕНО 3] Конструктор просто викликає батьківський
    # BaseService сам має обробити підключення та self.driver
    def __init__(self) -> None:
        super().__init__()

    # [ВИПРАВЛЕНО 4] Основний метод виконання запиту
    def run_query(self, cypher: str, params: Optional[Dict[str, Any]] = None, write: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Виконує cypher-запит і повертає список рядків (кожен як dict).
        """
        if not self._driver:
            log.error("Neo4j driver не ініціалізовано.")
            raise Exception("Neo4j driver не ініціалізовано.")
        
        try:
            # Використовуємо self.driver, успадкований від BaseService
            # (execute_query повертає (records, summary, keys))
            records, _, _ = self._driver.execute_query(
                cypher,
                params or {},
                database_=os.getenv("NEO4J_DATABASE", "neo4j")
                # Примітка: 'write' не є стандартним параметром для execute_query,
                # покладаємося на сесію або евристику драйвера.
            )
            # Перетворюємо записи neo4j.Record на звичайні dict
            return [dict(record) for record in records]
        except Exception as e:
            log.exception(f"Neo4j query failed: {cypher}")
            raise

    # [ВИПРАВЛЕНО 5] Всі інші методи тепер використовують наш виправлений run_query
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
            # 'write=True' тут не потрібен, оскільки run_query не приймає 'write'
            self.run_query(f"CALL gds.graph.drop('{graph_name}')")
        except Exception:
            log.debug("graph drop ignored or failed for %s", graph_name, exc_info=True)


# [ВИПРАВЛЕНО 6] Створюємо єдиний, модуль-рівневий екземпляр
query_runner = QueryRunner()