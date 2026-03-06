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
        truncated_text = text[:1000]
        active_categories = existing_categories if existing_categories else self.base_categories

        prompt = f"""
        You are a strict technical content classifier.
        Task: Assign the SINGLE most relevant category to the text.
        
        EXISTING CATEGORIES:
        {json.dumps(active_categories)}
        
        STRICT HIERARCHY OF RULES:
        1. PRIMARY GOAL: Select exactly ONE (1) category that represents the main topic.
        2. Maximum categories allowed: 2 (ONLY if the topics are equally dominant).
        3. PREFER existing categories. Choose from the list above if it's even 70% relevant.
        4. CREATE a new category ONLY if the text is completely unrelated to the list. 
        5. NEW categories must be a single English noun (e.g., "Botany").
        6. The summary MUST be in English and very dense.

        Content:
        "{truncated_text}"

        Return JSON format:
        {{
            "categories": ["MainCategory"],
            "is_unsafe": false,
            "summary": "Key entities and core mechanics only."
        }}
        """

        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                format='json',
                options={
                    'temperature': 0.05,
                    'num_ctx': 2048,
                    'num_predict': 150,
                }
            )
            
            result = json.loads(response['message']['content'])
            raw_cats = result.get("categories", [])
            if isinstance(raw_cats, str): raw_cats = [raw_cats]
                
            clean_cats = []
            active_cats_lower = {c.lower(): c for c in active_categories}
            
            for c in raw_cats:
                c_clean = str(c).strip()
                if len(c_clean) < 3 or c_clean.lower() in ["page", "text", "other", "general"]:
                    continue
                    
                if c_clean.lower() in active_cats_lower:
                    clean_cats.append(active_cats_lower[c_clean.lower()])
                else:
                    clean_cats.append(c_clean.title())
            
            final_cats = list(dict.fromkeys(clean_cats))[:2]
            
            result["categories"] = final_cats if final_cats else ["General"]
            return result
            
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return {
                "categories": ["General"],
                "is_unsafe": False,
                "summary": "Error analyzing"
            }