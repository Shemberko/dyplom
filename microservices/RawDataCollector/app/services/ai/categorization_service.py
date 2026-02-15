import json
import os
from typing import Dict, Any, List
from ollama import Client

class CategorizationService:
    def __init__(self, model_name: str = "llama3.2:1b"):
        self.model_name = model_name
        self.client = Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))

        self.categories = [
            "Technology", "News", "Social Media", "Shopping", 
            "Education", "Entertainment", "Finance", "Adult", "Gambling",
            "Health", "Science", "Travel", "Food", "Sports", "Gaming"
        ]

    def categorize(self, text: str) -> Dict[str, Any]:
        truncated_text = text[:800]

        prompt = f"""
        You are a smart content classifier.
        
        Task: Assign 1 to 3 categories to the text.
        
        OPTION 1 (Preferred): Choose from this list:
        {json.dumps(self.categories)}
        
        OPTION 2 (New Category): If needed, CREATE a new category name (short, descriptive noun).
        
        Rules:
        1. Return a list of strings in the "categories" field.
        2. Max 3 categories.
        3. Determine if content is unsafe.
        4. Write a short summary.
        
        Content:
        "{truncated_text}"

        Return JSON:
        {{
            "categories": ["Category1", "Category2"],
            "is_unsafe": boolean,
            "summary": "Short summary"
        }}
        """

        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                format='json',
                options={
                    'temperature': 0.3,
                    'num_ctx': 1024,
                    'num_predict': 128,
                },
                keep_alive='30m'
            )
            
            result = json.loads(response['message']['content'])
            
            cats = result.get("categories", [])
            if isinstance(cats, str):
                cats = [cats]
            
            clean_cats = []
            for c in cats:
                if len(c) > 2 and c.lower() not in ["page", "text", "other"]:
                    clean_cats.append(c)
            
            result["categories"] = clean_cats if clean_cats else ["General"]
            
            return result
            
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return {
                "categories": ["General"],
                "is_unsafe": False,
                "summary": "Error analyzing"
            }