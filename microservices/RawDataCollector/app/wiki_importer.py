import os
import logging
import requests
import time
import random
from typing import Dict, Any, List
from datetime import datetime, timezone

from services.record_processing.record_processor_service import RecordProcessorService
from services.record_processing.url_processor_service import UrlProcessorService

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class WikipediaImporter:
    def __init__(self, lang: str = "uk"):
        self.lang = lang
        self.processor = RecordProcessorService()
        self.url_processor = UrlProcessorService()
        
        self.api_url = f"https://{self.lang}.wikipedia.org/w/api.php"
        self.headers = { 
            "User-Agent": "RecommendationEngine/1.0 (student_project@example.com)" 
        }

    def fetch_category_batch(self, category_name: str, batch_size: int = 20) -> List[Dict[str, Any]]:
        list_params = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": f"Категорія:{category_name}",
            "cmlimit": 500,
            "cmtype": "page"
        }

        try:
            res = requests.get(self.api_url, params=list_params, headers=self.headers, timeout=15)
            res.raise_for_status()
            pages = [p for p in res.json().get("query", {}).get("categorymembers", []) if p.get("ns") == 0]
            
            if not pages:
                return []

            random.shuffle(pages)
            selected = pages[:batch_size] 
            
            entries = []
            for page in selected:
                prop_params = {
                    "action": "query",
                    "format": "json",
                    "pageids": page["pageid"],
                    "prop": "extracts|info|pageimages",
                    "inprop": "url",
                    "explaintext": 1,
                    "exintro": 0,
                    "piprop": "original"
                }
                
                try:
                    p_res = requests.get(self.api_url, params=prop_params, headers=self.headers, timeout=10)
                    p_data = p_res.json().get("query", {}).get("pages", {}).get(str(page["pageid"]), {})
                    
                    text = p_data.get("extract", "")
                    
                    if not text or len(text.strip()) < 100:
                        logging.warning(f"Стаття '{p_data.get('title')}' занадто коротка ({len(text)} симв.)")
                        continue

                    entries.append({
                        "raw_url": p_data.get("fullurl"),
                        "canonical_url": self.url_processor.normalize(p_data.get("fullurl")),
                        "title": f"{p_data.get('title')} - Wikipedia",
                        "meta_description": f"Wikipedia: {category_name}",
                        "text_content": text,
                        "image_url": p_data.get("original", {}).get("source"),
                        "visited_at_iso": datetime.now(timezone.utc).isoformat()
                    })
                except Exception as e:
                    logging.error(f"Не вдалося завантажити вміст сторінки {page['pageid']}: {e}")
                    continue

            logging.info(f"✅ Тема '{category_name}': Пакет сформовано ({len(entries)} статей).")
            return entries

        except Exception as e:
            logging.error(f"Помилка у '{category_name}': {e}")
            return []

    def process_entries(self, entries: List[Dict[str, Any]]) -> int:
        """Відправляє пакет статей у пайплайн обробки."""
        if not entries:
            return 0
        
        logging.info(f"📤 Відправка пакету ({len(entries)} шт.) у RecordProcessorService...")
        
        payload = {
            "user_id": None, 
            "user_email": None, 
            "entries": entries
        }
        
        try:
            self.processor.process(payload)
            return len(entries)
        except Exception as e:
            logging.error(f"❌ Критична помилка в RecordProcessorService: {e}")
            return 0

    def run_import(self, categories: List[str], articles_per_cat: int = 15):
        logging.info(f"🚀 Початок імпорту: {len(categories)} тем, по {articles_per_cat} статей.")
        
        total_saved = 0
        for cat in categories:
            logging.info(f"--- Обробка теми: {cat} ---")
            
            entries = self.fetch_category_batch(cat, batch_size=articles_per_cat)
            
            if entries:
                saved = self.process_entries(entries)
                total_saved += saved
                logging.info(f"✅ Тема {cat}: успішно опрацьовано {saved} статей.")
            else:
                logging.warning(f"⚠️ Тема {cat}: не вдалося отримати статті.")

        logging.info(f"🏁 Імпорт завершено. Всього додано в чергу обробки: {total_saved}")

def main():
    TOP_CATEGORIES = [
        "Комп'ютерні_науки", "Штучний_інтелект", "Програмування",
        "Кібербезпека", "Веб-розробка", "Фінанси", "Стартапи",
        "Маркетинг", "Економіка", "Менеджмент", "Космонавтика",
        "Астрономія", "Фізика", "Біотехнологія", "Психологія",
        "Освіта", "Сучасне_мистецтво", "Кінематограф", "Музика",
        "Філософія", "Соціологія", "Здоров'я", "Харчування",
        "Спорт", "Подорожі", "Екологія"
    ]
    
    importer = WikipediaImporter(lang="uk")
    importer.run_import(TOP_CATEGORIES, articles_per_cat=20)

if __name__ == "__main__":
    main()