import os
import json
import logging
import requests
from warcio.archiveiterator import ArchiveIterator
from typing import Dict, Any, List, Optional
from langdetect import detect, LangDetectException # <--- Новий імпорт для визначення мови
from datetime import datetime, timezone

# Припустимо, що ваш клас JsonMessageProcessor знаходиться у тому ж проекті
from services.json_message_processor import JsonMessageProcessor 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- КОНСТАНТИ COMMON CRAWL ---
CC_BASE_URL = 'https://data.commoncrawl.org/' 
CC_WET_FILE_PATH = 'crawl-data/CC-MAIN-2023-50/segments/1700679099281.67/wet/CC-MAIN-20231128083443-20231128113443-00000.warc.wet.gz'

# --- МОЖЛИВІ МОВИ ---
TARGET_LANGUAGES = ['en', 'uk']
BATCH_SIZE = 100 # Розмір пакета для запису в БД

class CommonCrawlImporter:
    
    def __init__(self, processor: JsonMessageProcessor):
        self.processor = processor

    def _convert_to_processor_format(self, url: str, content: str, language: str) -> Optional[Dict[str, Any]]:
        """
        Перетворює один запис WET у потрібний формат для масиву даних.
        """
        
        # Спроба витягти заголовок з перших 100 символів тексту
        title_estimate = content.split('\n\n', 1)[0][:100].strip()
        
        # Створення структури, яка відповідає log-entry (частині повідомлення RabbitMQ)
        log_entry = {
            "info": {
                "url": url,
                "title": title_estimate,
                "metaDescription": f"Common Crawl Data ({language})",
                "textSample": content,
                # Додаємо мову для потенційного використання в Embeddings/Neo4j
                "language": language, 
                # Фіктивні дані для VISIT
                "active": 60000,
                "totalOpen": 120000,
                "visitedAt": datetime.now(timezone.utc).isoformat()
            }
        }
        return log_entry

    def _detect_language(self, text: str) -> Optional[str]:
        """Визначає мову тексту за допомогою langdetect."""
        try:
            # langdetect вимагає мінімум тексту для коректної роботи
            if len(text.strip()) < 50:
                return None
            
            lang = detect(text)
            return lang if lang in TARGET_LANGUAGES else None
        except LangDetectException:
            return None
        except Exception as e:
            logging.debug(f"Помилка визначення мови: {e}")
            return None

    def process_batch(self, batch_data: List[Dict[str, Any]]) -> int:
        """
        ОНОВЛЕНО: Імітує пакувальника повідомлень RabbitMQ та передає їх у процесор.
        
        Оскільки ваш JsonMessageProcessor очікує лише ОДНЕ JSON-повідомлення 
        і обробляє його як єдину транзакцію, ми імітуємо це, упаковуючи 
        весь масив у фіктивний формат користувача.
        """
        
        # Використовуємо фіктивний user_id для імітації сеансу
        MOCK_USER_ID = "commoncrawl_importer_user"
        
        # Створюємо одне велике JSON-повідомлення у форматі, очікуваному JsonMessageProcessor
        processor_message = {
            "log": batch_data # Масив відфільтрованих лог-записів
        }
        
        # Перетворюємо на байт-повідомлення
        body = json.dumps(processor_message).encode('utf-8')
        
        try:
            # Передаємо один великий пакет у процесор
            success = self.processor.process(body)
            return len(batch_data) if success else 0
        except Exception as e:
            logging.error(f"Критична помилка пакетної обробки ({len(batch_data)} записів): {e}", exc_info=True)
            return 0


    def download_and_process_wet(self, key_path: str):
        full_url = CC_BASE_URL + key_path
        logging.info(f"Завантаження файлу WET (HTTPS): {full_url}")
        
        try:
            response = requests.get(full_url, stream=True, timeout=300) 
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Помилка завантаження файлу WET через HTTPS {full_url}: {e}")
            return

        stream = response.raw
        
        total_processed = 0
        current_batch = []
        
        logging.info(f"🔎 Початок парсингу з фільтрацією на мови {TARGET_LANGUAGES}...")

        try:
            for record in ArchiveIterator(stream):
                if record.rec_type == 'conversion':
                    url = record.rec_headers.get_header('WARC-Target-URI')
                    content = record.content_stream().read().decode('utf-8', errors='ignore')
                    
                    if url and content.strip():
                        
                        # --- ФІЛЬТРАЦІЯ ЗА МОВОЮ ---
                        language = self._detect_language(content)
                        
                        if language:
                            log_entry = self._convert_to_processor_format(url, content, language)
                            current_batch.append(log_entry)
                            
                            if len(current_batch) >= BATCH_SIZE:
                                # Обробка пакета
                                success_count = self.process_batch(current_batch)
                                total_processed += success_count
                                current_batch = [] # Очищення пакета
                                
                                logging.info(f"Оброблено {total_processed} записів ({language}).")

            # Обробка останнього (неповного) пакета
            if current_batch:
                success_count = self.process_batch(current_batch)
                total_processed += success_count

        except Exception as e:
            logging.error(f"Помилка парсингу або обробки: {e}", exc_info=True)
            
        logging.info(f"--- Завершено обробку. Успішно завантажено {total_processed} цільових записів. ---")


# --- ПРИКЛАД ВИКОРИСТАННЯ (MAIN) ---

def main():
    try:
        processor = JsonMessageProcessor() 
        importer = CommonCrawlImporter(processor)
        importer.download_and_process_wet(CC_WET_FILE_PATH) 
        
    except Exception as e:
        logging.critical(f"Критична помилка виконання імпортера: {e}")

if __name__ == "__main__":
    main()