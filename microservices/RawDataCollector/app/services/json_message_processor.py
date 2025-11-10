from typing import Any, Dict, Optional, List
import json

from .helpers.url_processor_service import UrlProcessorService
from .gemini.embeddings_service import EmbeddingsService
from .neo4j.history_service import HistoryService
from datetime import datetime


class JsonMessageProcessor:
    """
    Parse incoming Rabbit message (bytes), build embeddings, clean URL and
    persist User / Page / VISIT using existing services.
    """

    def __init__(
        self,
        url_processor: Optional[UrlProcessorService] = None,
        embeddings_svc: Optional[EmbeddingsService] = None,
        history_svc: Optional[HistoryService] = None,
    ):
        self.url_processor = url_processor or UrlProcessorService()
        self.embeddings = embeddings_svc or EmbeddingsService()
        self.history = history_svc or HistoryService()

    def _loads_body(self, body: bytes | str) -> Optional[Dict[str, Any]]:
        """
        Accept bytes or str. Decode bytes as UTF-8, parse JSON.
        Handle double-encoded JSON (string containing JSON).
        Return dict or None.
        """
        try:
            if isinstance(body, bytes):
                s = body.decode("utf-8")
            elif isinstance(body, str):
                s = body
            else:
                return None
        except Exception:
            return None

        try:
            data = json.loads(s)
        except Exception:
            return None

        # handle double-encoded JSON (JSON string inside JSON)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                pass

        if not isinstance(data, dict):
            return None
        return data

    def _build_text_for_embedding(self, info: Dict[str, Any]) -> str:
        parts: List[str] = []
        for k in ("title", "metaDescription", "textSample"):
            v = info.get(k)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
        return "\n\n".join(parts) if parts else info.get("textSample", "") or ""

    def process(self, body: bytes) -> bool:
        """
        Process raw message bytes. Returns True on success, False otherwise.
        """
        data = self._loads_body(body)

        if not data:
            return False

        user_info = (data.get("user") or {}).get("info", {}) if isinstance(data, dict) else {}
        user_id = user_info.get("id")
        user_email = user_info.get("email")
        if not user_id:
            return False

        try:
            # create/update user
            user_props = {}
            if user_email:
                user_props["email"] = user_email

            self.history.create_or_update_user(user_id, user_props)

            # process log entries (pages)
            for entry in (data.get("log") or []):
                info = entry.get("info", {}) if isinstance(entry, dict) else {}
                raw_url = info.get("url")
                if not raw_url:
                    continue

                canonical = self.url_processor.normalize(raw_url)

                # build embedding text and compute embedding
                text_for_embedding = self._build_text_for_embedding(info)
                embedding: List[float] = []
                try:
                    emb = self.embeddings(text_for_embedding)
                    # embeddings service returns list[float] or [] on error
                    if isinstance(emb, list) and emb:
                        embedding = emb
                except Exception:
                    embedding = []


                page_props = {
                    "title": info.get("title"),
                    "metaDescription": info.get("metaDescription"),
                    "textSample": info.get("textSample"),
                    "active": info.get("active"),
                    "totalOpen": info.get("totalOpen"),
                    "original_url": raw_url,
                }
                if embedding:
                    page_props["embedding"] = embedding

                # persist page and vis
            
                self.history.create_or_update_page(canonical, page_props)
                # record visit time and source; include active/totalOpen as deltas to be summed by history service
                visited_at = datetime.utcnow().isoformat() + "Z"
                visit_props = {"source": "browser-extension", "visitedAt": [visited_at]}

                # include numeric fields when available (coerce to int if possible)
                active = info.get("active")
                if active is not None:
                    try:
                        visit_props["active"] = int(active)
                    except Exception:
                        pass

                total_open = info.get("totalOpen")
                if total_open is not None:
                    try:
                        visit_props["totalOpen"] = int(total_open)
                    except Exception:
                        pass

                breakpoint()

                self.history.create_or_update_visit(user_id=user_id, page_url=canonical, visit_props=visit_props)

        except Exception:
            return False

        return True
