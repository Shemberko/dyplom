from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
import numpy as np

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
            should_keep = self.filtration.should_process(raw_url, title, text_content)
            if not should_keep:
                return

            existing_categories = self.history.get_categories()
            ai_data = self.categorization.categorize(text_content, existing_categories)
            categories_list = ai_data.get("categories", ["General"])
            ai_summary = ai_data.get("summary", "")
            
            categories_payload = []
            for cat_name in categories_list:
                cat_vector = self.embeddings(cat_name)
                categories_payload.append({
                    "name": cat_name,
                    "embedding": cat_vector
                })
        
            text_for_embedding = ai_summary if len(ai_summary.strip()) > 10 else text_content
            page_vector = self.embeddings(text_for_embedding)
            
            if page_vector:
                v = np.array(page_vector)
                norm = np.linalg.norm(v)
                if norm > 0:
                    page_vector = (v / norm).tolist()
            
            final_image = entry.get("image_url")
            if not final_image:
                final_image = self.image_fetcher.get_preview_image(canonical_url)

            page_props = {
                "title": title,
                "meta_description": entry.get("meta_description"),
                "text_sample": text_content, 
                "image": final_image,
                "ai_summary": ai_summary,
                "is_unsafe": ai_data.get("is_unsafe", False)
            }
            if page_vector:
                page_props["text_embedding"] = page_vector

            self.history.create_or_update_page(
                canonical_url, 
                page_props, 
                categories_payload
            )
        visited_at = entry.get("visited_at_iso") or datetime.now(timezone.utc).isoformat()
        visit_props = {
            "source": "browser-extension",
            "visitedAt": [visited_at]
        }
        
        if entry.get("active_time_mins"):
            visit_props["active_time"] = entry.get("active_time_mins")
        if entry.get("total_open_time_mins"):
            visit_props["total_open_time"] = entry.get("total_open_time_mins")

        if user_id:
            self.history.create_or_update_visit(
                user_id=user_id, 
                page_url=canonical_url, 
                visit_props=visit_props
            )