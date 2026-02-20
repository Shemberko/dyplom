import json
import os
from typing import Dict, Any, List
from ollama import Client

class CategorizationService:
    def __init__(self, model_name: str = "llama3.2:1b"):
        self.model_name = model_name
        self.client = Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))

        self.base_categories = [
            "Technology", "News", "Entertainment", "Education", 
            "Finance", "Shopping", "Health", "Science", "General"
        ]

    def categorize(self, text: str, existing_categories: List[str] = None) -> Dict[str, Any]:
        truncated_text = text[:800]
        
        # Використовуємо передані з БД категорії, або базові
        active_categories = existing_categories if existing_categories else self.base_categories

        prompt = f"""
        You are a smart content classifier.
        Task: Assign 1 to 3 categories to the text.
        
        EXISTING CATEGORIES:
        {json.dumps(active_categories)}
        
        CRITICAL RULES:
        1. STRONGLY PREFER using categories from the EXISTING CATEGORIES list.
        2. ONLY if the text's main topic is completely missing from the list, you may create a NEW category.
        3. A new category MUST be a broad, single noun (e.g. "Agriculture", NOT "Growing Tomatoes").
        4. Return a JSON object with a list of strings in the "categories" field.
        5. Determine if content is unsafe.
        6. Write a short summary.
        7. Return categiries only in ENGLISH.

        Content:
        "{truncated_text}"

        Return JSON:
        {{
            "categories": ["Cat1", "Cat2"],
            "is_unsafe": false,
            "summary": "Short summary"
        }}
        """

        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                format='json',
                options={
                    'temperature': 0.1, # Низька температура: змушує віддавати перевагу списку, а не фантазувати
                    'num_ctx': 1024,
                    'num_predict': 128,
                },
                keep_alive='30m'
            )
            
            result = json.loads(response['message']['content'])
            
            raw_cats = result.get("categories", [])
            if isinstance(raw_cats, str):
                raw_cats = [raw_cats]
                
            # --- ЗАХИСНА СІТКА (POST-PROCESSING) ---
            clean_cats = []
            active_cats_lower = {c.lower(): c for c in active_categories} # Словник для швидкого пошуку
            
            for c in raw_cats:
                c_clean = str(c).strip()
                
                # Відкидаємо відверте сміття
                if len(c_clean) < 3 or c_clean.lower() in ["page", "text", "other", "content", "website"]:
                    continue
                    
                # Якщо модель повернула слово, яке вже є, але в іншому регістрі (напр. "technology") -> беремо існуюче ("Technology")
                if c_clean.lower() in active_cats_lower:
                    clean_cats.append(active_cats_lower[c_clean.lower()])
                else:
                    # Якщо це дійсно НОВА категорія: робимо її з Великої Літери і додаємо
                    new_cat_title = c_clean.title()
                    clean_cats.append(new_cat_title)
            
            # Якщо після чистки нічого не залишилось
            result["categories"] = list(set(clean_cats)) if clean_cats else ["General"]
            
            return result
            
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return {
                "categories": ["General"],
                "is_unsafe": False,
                "summary": "Error analyzing"
            }