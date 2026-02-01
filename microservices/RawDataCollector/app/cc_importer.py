import os
import logging
import requests
from warcio.archiveiterator import ArchiveIterator
from typing import Dict, Any, List, Optional
from langdetect import detect, LangDetectException
from datetime import datetime, timezone

# Імпорти ваших сервісів
from services.record_processing.record_processor_service import RecordProcessorService
from services.record_processing.url_processor_service import UrlProcessorService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CC_BASE_URL = 'https://data.commoncrawl.org/' 
CC_WET_FILE_PATH = 'crawl-data/CC-MAIN-2023-50/segments/1700679099281.67/wet/CC-MAIN-20231128083443-20231128113443-00000.warc.wet.gz'

TARGET_LANGUAGES = ['en', 'uk']
BATCH_SIZE = 50 

class CommonCrawlImporter:
    
    def __init__(self):
        self.processor = RecordProcessorService()
        self.url_processor = UrlProcessorService()

    def _convert_to_processor_format(self, url: str, content: str, language: str) -> Optional[Dict[str, Any]]:
        """
        Перетворює запис WET у формат словника.
        """
        title_estimate = content.split('\n', 1)[0][:150].strip()
        canonical = self.url_processor.normalize(url)
        entry = {
            "raw_url": url,
            "canonical_url": canonical,
            "title": title_estimate,
            "meta_description": f"Common Crawl Data ({language})",
            "text_content": content,
            "image_url": None, 
        }
        return entry

    def _detect_language(self, text: str) -> Optional[str]:
        """Визначає мову тексту."""
        try:
            if len(text.strip()) < 100: 
                return None
            
            lang = detect(text)
            return lang if lang in TARGET_LANGUAGES else None
        except LangDetectException:
            return None
        except Exception:
            return None

    def process_batch(self, batch_entries: List[Dict[str, Any]]) -> int:
        """
        Відправляє пакет записів у RecordProcessorService БЕЗ користувача.
        """
        if not batch_entries:
            return 0

        payload = {
            "user_id": None, 
            "user_email": None,
            "entries": batch_entries
        }
        
        try:
            self.processor.process(payload)
            return len(batch_entries)
        except Exception as e:
            logging.error(f"Критична помилка пакетної обробки: {e}", exc_info=True)
            return 0

    def download_and_process_wet(self, key_path: str):
        full_url = CC_BASE_URL + key_path
        logging.info(f"🚀 Завантаження файлу WET: {full_url}")
        
        try:
            response = requests.get(full_url, stream=True, timeout=300) 
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Помилка завантаження {full_url}: {e}")
            return

        stream = response.raw
        
        total_processed = 0
        current_batch = []
        
        logging.info(f"🔎 Початок парсингу (мови: {TARGET_LANGUAGES})...")

        try:
            for record in ArchiveIterator(stream):
                if record.rec_type == 'conversion':
                    url = record.rec_headers.get_header('WARC-Target-URI')
                    content = record.content_stream().read(1024 * 1024).decode('utf-8', errors='ignore')
                    
                    if url and content.strip():
                        language = self._detect_language(content[:2000])
                        
                        if language:
                            entry = self._convert_to_processor_format(url, content, language)
                            current_batch.append(entry)
                            
                            if len(current_batch) >= BATCH_SIZE:
                                count = self.process_batch(current_batch)
                                total_processed += count
                                current_batch = [] 
                                logging.info(f"💾 Збережено (тільки Page nodes) {total_processed} записів...")

            if current_batch:
                count = self.process_batch(current_batch)
                total_processed += count

        except Exception as e:
            logging.error(f"Помилка циклу парсингу: {e}", exc_info=True)
            
        logging.info(f"🏁 Завершено. Всього імпортовано сторінок: {total_processed}")


def main():
    try:
        importer = CommonCrawlImporter()
        importer.download_and_process_wet(CC_WET_FILE_PATH) 
    except Exception as e:
        logging.critical(f"Fatal error: {e}")

if __name__ == "__main__":
    main()