# ...existing code...
import os
from typing import Dict, Any, Optional
from neo4j import Driver
from .base_service import BaseService

class HistoryService(BaseService):
    def __init__(self, driver: Optional[Driver] = None,
                 uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        super().__init__(uri=uri, user=user, password=password)
        if driver is not None:
            self._driver = driver

    def create_or_update_user(self, user_id: str, props: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        props = props or {}
        props["id"] = user_id
        return super().create_or_update_node("User", "id", props)

    def create_or_update_page(self, url: str, props: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        props = props or {}
        props["url"] = url
        return super().create_or_update_node("Page", "url", props)
    
    def page_exists(self, url: str) -> bool:
        node = super().get_node("Page", "url", url)
        return node is not None

    def create_or_update_visit(self,
                               user_id: str,
                               page_url: str,
                               visit_props: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        visit_props = visit_props or {}
        # Гарантуємо, що вузли існують / оновлені
        self.create_or_update_user(user_id, {})
        self.create_or_update_page(page_url, {})
        # Створюємо або оновлюємо зв'язок VISIT
        return super().create_relationship(
            start_label="User", start_key="id", start_val=user_id,
            end_label="Page", end_key="url", end_val=page_url,
            rel_type="VISIT", rel_properties=visit_props,
            additive_metrics=["active_time", "total_open_time"]
        )