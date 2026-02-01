import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from .url_processor_service import UrlProcessorService

@dataclass
class ProcessedLogEntry:
    raw_url: str
    canonical_url: str
    title: str
    text_content: str
    meta_description: str
    image_url: Optional[str]
    active_time_mins: Optional[float]
    total_open_time_mins: Optional[float]
    visited_at_iso: str

class FeatureExtractionService:
    def __init__(self, url_processor: Optional[UrlProcessorService] = None):
        self.url_processor = url_processor or UrlProcessorService()

    def parse_and_extract(self, body: bytes) -> Optional[hash]:
        data = self._loads_body(body)
        if not data:
            return None

        user_info = (data.get("user") or {}).get("info", {})
        user_id = user_info.get("id")
        user_email = user_info.get("email")

        entries = []
        raw_logs = data.get("log") or []
        
        for entry in raw_logs:
            info = entry.get("info", {})
            raw_url = info.get("url")
            if not raw_url:
                continue

            canonical = self.url_processor.normalize(raw_url)
            text_content = self._build_text_sample(info)
            active = info.get("active")
            total = info.get("totalOpen")
            
            entries.append({
                "raw_url":raw_url,
                "canonical_url":canonical,
                "title":info.get("title", ""),
                "meta_description":info.get("metaDescription", ""),
                "text_content":text_content,
                "image_url":info.get("previewImage"),
                "active_time_mins":active / 60000 if active else None,
                "total_open_time_mins":total / 60000 if total else None,
                "visited_at_iso" : entry.get("visitedAt")
            })

        return {
            "user_id": user_id,
            "user_email": user_email,
            "entries": entries
        }

    def _loads_body(self, body: bytes | str) -> Optional[Dict[str, Any]]:
        try:
            s = body.decode("utf-8") if isinstance(body, bytes) else body
            data = json.loads(s)
            if isinstance(data, str): data = json.loads(data)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _build_text_sample(self, info: Dict[str, Any]) -> str:
        parts = []
        for k in ("title", "metaDescription", "textSample"):
            v = info.get(k)
            if v and str(v).strip():
                parts.append(str(v).strip())
        return "\n\n".join(parts)