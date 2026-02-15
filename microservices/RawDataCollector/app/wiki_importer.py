import os
import logging
import requests
import time
from typing import Dict, Any, List
from datetime import datetime, timezone

from services.record_processing.record_processor_service import RecordProcessorService
from services.record_processing.url_processor_service import UrlProcessorService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WikipediaImporter:
    def __init__(self, lang: str = "uk"):
        self.lang = lang
        self.processor = RecordProcessorService()
        self.url_processor = UrlProcessorService()
        
        self.api_url = f"https://{self.lang}.wikipedia.org/w/api.php"
        self.headers = { "User-Agent": "RecommendationEngine/1.0 (student_project@example.com)" }

    def fetch_random_batch(self, batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        Завантажує випадкові статті з Вікіпедії (URL, текст, картинка).
        Максимальний batch_size для Вікіпедії = 20 (для звичайних юзерів).
        """
        params = {
            "action": "query",
            "format": "json",
            "generator": "random",
            "grnnamespace": 0,
            "grnlimit": batch_size,
            "prop": "extracts|info|pageimages",
            "inprop": "url",
            "explaintext": 1,
            "piprop": "original"
        }

        try:
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logging.error(f"Помилка API Вікіпедії: {e}")
            return []

        pages = data.get("query", {}).get("pages", {})
        entries = []

        for page_id, page_data in pages.items():
            title = page_data.get("title", "")
            raw_url = page_data.get("fullurl", "")
            text_content = page_data.get("extract", "")
            
            image_url = page_data.get("original", {}).get("source")

            if not text_content or len(text_content.strip()) < 500:
                continue

            canonical_url = self.url_processor.normalize(raw_url)

            entries.append({
                "raw_url": raw_url,
                "canonical_url": canonical_url,
                "title": f"{title} - Wikipedia",
                "meta_description": f"Wikipedia article about {title}",
                "text_content": text_content,
                "image_url": image_url,
                "visited_at_iso": datetime.now(timezone.utc).isoformat()
            })

        return entries

    def process_entries(self, entries: List[Dict[str, Any]]) -> int:
        """Відправляє записи у ваш пайплайн обробки."""
        if not entries:
            return 0

        payload = {
            "user_id": None,
            "user_email": None,
            "entries": entries
        }

        try:
            self.processor.process(payload)
            return len(entries)
        except Exception as e:
            logging.error(f"Помилка під час обробки пайплайну: {e}")
            return 0

    def run_import(self, total_articles: int = 100):
        """
        Головний цикл імпорту.
        """
        logging.info(f"🚀 Початок імпорту {total_articles} статей з Вікіпедії ({self.lang})...")
        
        articles_processed = 0
        batch_size = 10

        while articles_processed < total_articles:
            logging.info(f"Завантаження пакету... ({articles_processed}/{total_articles})")
            
            entries = self.fetch_random_batch(batch_size=batch_size)
            if not entries:
                logging.warning("Отримано пустий пакет, повторна спроба через 5 сек...")
                time.sleep(5)
                continue

            saved_count = self.process_entries(entries)
            articles_processed += saved_count
            
            logging.info(f"✅ Збережено {saved_count} статей. Всього: {articles_processed}")
            
            time.sleep(2)

        logging.info("🏁 Імпорт успішно завершено!")


def main():
    TARGET_COUNT = 50 
    
    importer = WikipediaImporter(lang="uk")
    importer.run_import(total_articles=TARGET_COUNT)

if __name__ == "__main__":
    main()