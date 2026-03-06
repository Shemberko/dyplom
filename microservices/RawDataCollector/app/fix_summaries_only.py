import sys
import json
import os
import numpy as np
from ollama import Client

from services.ai.embeddings_service import EmbeddingsService
from services.neo4j.base_service import BaseService

print("🚀 Ініціалізація сервісів...")
emb_service = EmbeddingsService()
neo4j_client = BaseService()
ollama_client = Client(host=os.getenv("OLLAMA_HOST", "http://ollama_service:11434"))
MODEL_NAME = "llama3.2:1b"

def generate_summary(text: str) -> str:
    if not text or len(text.strip()) < 10:
        return ""
        
    prompt = f"""
    You are a precise technical content analyzer.
    Task: Extract a dense semantic summary.
    
    RULES:
    - Write a highly dense, keyword-rich summary of the core concepts.
    - DO NOT use filler words (e.g., avoid "This article discusses...").
    - Maximum length: 3 sentences.
    - The summary MUST be STRICTLY IN ENGLISH.

    Content:
    "{text[:800]}"

    Return JSON strictly:
    {{
        "summary": "dense semantic summary here"
    }}
    """

    try:
        response = ollama_client.chat(
            model=MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}],
            format='json',
            options={'temperature': 0.1, 'num_ctx': 1024, 'num_predict': 128}
        )
        result = json.loads(response['message']['content'])
        return result.get("summary", "").strip()
    except Exception as e:
        print(f"   [!] Помилка Ollama: {e}")
        return ""

fetch_query = """
MATCH (p:Page) 
WHERE p.ai_summary IS NULL 
   OR p.ai_summary = '' 
   OR p.ai_summary = 'Error analyzing'
RETURN p.url AS url, p.title AS title, p.text_sample AS text_content
"""

try:
    pages = neo4j_client.run_query(fetch_query)

    if not pages:
        print("⚠️ Немає сторінок для оновлення.")
    else:
        print(f"📊 Знайдено {len(pages)} сторінок. Починаємо генерацію описів...")
        
        updated = 0
        for p in pages:
            url = p['url']
            title = p['title']
            text = p['text_content']
            
            print(f"🧠 Аналізую: {title}...")
            new_summary = generate_summary(text)
            
            if new_summary:
                # Робимо вектор з нового висновку
                vec = emb_service(new_summary)
                normalized_vec = None
                
                if vec:
                    v = np.array(vec)
                    norm = np.linalg.norm(v)
                    if norm > 0:
                        normalized_vec = (v / norm).tolist()
                
                # Оновлюємо БД
                update_q = """
                MATCH (page:Page {url: $url}) 
                SET page.ai_summary = $summary,
                    page.text_embedding = $emb
                """
                neo4j_client.run_query(update_q, {
                    'url': url, 
                    'summary': new_summary, 
                    'emb': normalized_vec
                })
                updated += 1
                print(f"   ✅ Збережено: {new_summary[:60]}...")
            else:
                print(f"   ❌ Пропущено (порожній результат).")

        print(f"\n🎉 Оновлено {updated} сторінок!")

finally:
    neo4j_client.close()
