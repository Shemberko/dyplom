import sys
import numpy as np
sys.path.append('/app')

from services.ai.embeddings_service import EmbeddingsService
from services.neo4j.query_runner import query_runner as neo4j_client

print("🚀 Ініціалізація сервісу ембедингів...")
emb_service = EmbeddingsService()

fetch_query = """
MATCH (p:Page) 
WHERE p.ai_summary IS NOT NULL AND p.ai_summary <> ''
RETURN p.url AS url, p.title AS title, p.ai_summary AS summary
"""

pages = neo4j_client.run_query(fetch_query)

if not pages:
    print("⚠️ Не знайдено сторінок із ai_summary.")
else:
    print(f"📊 Знайдено {len(pages)} сторінок. Починаємо генерацію нових векторів...")
    updated = 0
    for p in pages:
        summary = p['summary']
        # Генеруємо вектор з короткого висновку
        vec = emb_service(summary)
        
        if vec:
            # Нормалізуємо
            v = np.array(vec)
            norm = np.linalg.norm(v)
            if norm > 0:
                vec = (v / norm).tolist()
            
            # Оновлюємо БД
            update_q = "MATCH (page:Page {url: $url}) SET page.text_embedding = $emb"
            neo4j_client.run_query(update_q, {'url': p['url'], 'emb': vec})
            updated += 1
            
            if updated % 10 == 0:
                print(f"🔄 Опрацьовано {updated} сторінок...")

    print(f"✅ Успіх! Оновлено {updated} векторів.")
