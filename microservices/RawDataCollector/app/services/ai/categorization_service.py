import json
import os
from typing import Dict, Any
from ollama import Client

class CategorizationService:
    def __init__(self, model_name: str = "llama3.2:1b"):
        self.model_name = model_name
        self.client = Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))

        self.categories = [
            "Technology", "News", "Social Media", "Shopping", 
            "Education", "Entertainment", "Finance", "Adult", "Gambling",
            "Health", "Science", "Travel", "Food"
        ]

    def categorize(self, text: str) -> Dict[str, Any]:
        truncated_text = text[:800]

        prompt = f"""
        You are a smart content classifier.
        
        Task: Classify the text into a category.
        
        OPTION 1 (Preferred): Choose from this list:
        {json.dumps(self.categories)}
        
        OPTION 2 (New Category): If the content clearly DOES NOT fit the list, CREATE a new category name.
        
        Rules for New Categories:
        1. Must be short (1-3 words).
        2. Must be descriptive nouns (e.g., "Beekeeping", "Quantum Physics", "Architecture").
        3. DO NOT use generic words like "Page", "Website", "Home", "Info", "Miscellaneous".
        
        Content:
        "{truncated_text}"

        Return JSON:
        {{
            "category": "String (from list OR new)",
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
                    'num_predict': 100,
                },
                keep_alive='30m'
            )
            
            result = json.loads(response['message']['content'])
            
            cat = result.get("category", "General")
            
            if len(cat) < 3 or cat.lower() in ["page", "text", "content", "other"]:
                result["category"] = "General"
                
            return result
            
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return {
                "category": "General",
                "is_unsafe": False,
                "summary": "Error analyzing"
            }