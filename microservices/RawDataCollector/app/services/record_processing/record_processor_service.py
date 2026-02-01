from datetime import datetime, timezone
from typing import List, Optional, Any, Dict

# Імпорти ваших сервісів
from ..neo4j.history_service import HistoryService
from ..ai.embeddings_service import EmbeddingsService
from ..ai.filtration_service import FiltrationService
from ..ai.categorization_service import CategorizationService
from .image_fetcher_service import ImageFetcherService

class RecordProcessorService:
    def __init__(self):
        self.history = HistoryService()
        self.embeddings = EmbeddingsService()
        self.filtration = FiltrationService()
        self.categorization = CategorizationService()
        self.image_fetcher = ImageFetcherService()

    def process(self, data: Dict[str, Any]):
        """
        Приймає словник з даними про повідомлення.
        Очікувана структура data:
        {
            "user_id": "...",
            "user_email": "...",
            "entries": [ ...список словників entry... ]
        }
        """
        user_id = data.get("user_id")
        user_email = data.get("user_email")

        if user_id:
            user_props = {}
            if user_email:
                user_props["email"] = user_email
            
            if user_props:
                self.history.create_or_update_user(user_id, user_props)

        entries = data.get("entries", [])
        for entry in entries:
            self._process_single_entry(user_id, entry)

    def _process_single_entry(self, user_id: Optional[str], entry: Dict[str, Any]):
        """
        Оптимізована версія: перевіряє наявність сторінки перед запуском AI-фільтрів.
        """
        raw_url = entry.get("raw_url")
        canonical_url = entry.get("canonical_url")
        if not canonical_url or not raw_url:
            return

        title = entry.get("title", "")
        text_content = entry.get("text_content", "")

        page_exists = self.history.page_exists(canonical_url)

        if page_exists:
            page_props = {
                "title": title,
                "meta_description": entry.get("meta_description"),
            }
            
            if entry.get("image_url"):
                 page_props["image"] = entry.get("image_url")

            self.history.create_or_update_page(canonical_url, page_props)

        else:
            # --- СЦЕНАРІЙ Б: НОВА СТОРІНКА ---
            # Тільки тут запускаємо важку артилерію (AI)
            
            should_keep = self.filtration.should_process(
                raw_url, title, text_content
            )
            if not should_keep:
                return

            # Аналіз контенту
            ai_data = self.categorization.categorize(text_content)
            vector = self.embeddings(text_content)
            
            final_image = entry.get("image_url")
            if not final_image:
                # Фечимо картинку тільки для нових сторінок, де її немає
                # (Або можна додати логіку оновлення, якщо в існуючої немає)
                final_image = self.image_fetcher.get_preview_image(canonical_url)

            page_props = {
                "title": title,
                "meta_description": entry.get("meta_description"),
                "text_sample": text_content, 
                "image": final_image,
                "category": ai_data.get("category"),
                "ai_summary": ai_data.get("summary"),
                "is_unsafe": ai_data.get("is_unsafe", False)
            }
            
            if vector:
                page_props["text_embedding"] = vector

            self.history.create_or_update_page(canonical_url, page_props)

        visited_at = entry.get("visited_at_iso") or datetime.now(timezone.utc).isoformat()
        visit_props = {
            "source": "browser-extension",
            "visitedAt": [visited_at]
        }
        
        active_time = entry.get("active_time_mins")
        if active_time:
            visit_props["active_time"] = active_time
            
        total_open = entry.get("total_open_time_mins")
        if total_open:
            visit_props["total_open_time"] = total_open

        if user_id:
            self.history.create_or_update_visit(
                user_id=user_id, 
                page_url=canonical_url, 
                visit_props=visit_props
            )