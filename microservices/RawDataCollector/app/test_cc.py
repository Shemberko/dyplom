import os
import logging
import requests
from warcio.archiveiterator import ArchiveIterator
from typing import Dict, Any

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- КОНСТАНТИ COMMON CRAWL ---
CC_BASE_URL = 'https://data.commoncrawl.org/' 

# Використовуємо перевірений робочий шлях
CC_WET_FILE_PATH = 'crawl-data/CC-MAIN-2023-50/segments/1700679099281.67/wet/CC-MAIN-20231128083443-20231128113443-00000.warc.wet.gz'


def download_and_test_wet():
    """
    Завантажує та парсить перші 100 записів WET-файлу для перевірки зв'язку.
    Не має жодних залежностей від Neo4j/Gemini.
    """
    full_url = CC_BASE_URL + CC_WET_FILE_PATH
    
    logging.info(f"🔗 Спроба завантаження файлу WET (HTTPS): {full_url}")
    
    try:
        # Використовуємо requests.get() з потоковим режимом
        response = requests.get(full_url, stream=True, timeout=300) 
        response.raise_for_status() # Обробляємо помилки HTTP (4xx або 5xx)
        
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Критична помилка завантаження файлу WET: {e}")
        return

    # response.raw надає файлоподібний об'єкт, необхідний для warcio
    stream = response.raw
    
    count = 0
    MAX_RECORDS = 100

    logging.info(f"🔎 Початок парсингу (вивід перших {MAX_RECORDS} записів)...")
    
    try:
        for record in ArchiveIterator(stream):
            if record.rec_type == 'conversion':
                url = record.rec_headers.get_header('WARC-Target-URI')
                # Читаємо вміст запису (невеликий шматок для виводу)
                content = record.content_stream().read().decode('utf-8', errors='ignore')
                
                if url and content.strip():
                    count += 1
                    
                    # Виводимо інформацію про сторінку
                    print("-" * 50)
                    print(f"[{count}] URL: {url}")
                    # Виводимо перші 200 символів чистого тексту
                    print(f"Текст (зразк): {content.strip()[:200]}...")
                    
                    if count >= MAX_RECORDS:
                        logging.info(f"✅ Успішно оброблено {MAX_RECORDS} записів. З'єднання та парсинг працюють.")
                        break
                        
    except Exception as e:
        logging.error(f"❌ Помилка парсингу WET-файлу: {e}", exc_info=True)
        
    if count < MAX_RECORDS:
         logging.warning(f"⚠️ Парсинг завершено, але оброблено лише {count} записів (менше ніж {MAX_RECORDS}).")
    
    logging.info("--- Кінець перевірки ---")


if __name__ == "__main__":
    download_and_test_wet()