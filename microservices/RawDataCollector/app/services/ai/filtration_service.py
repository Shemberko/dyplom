import re
import os
from ollama import Client
from typing import Tuple

class FiltrationService:
    def __init__(self, model_name: str = "llama3.2:1b"):
        self.model_name = model_name
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        self.client = Client(host=ollama_host)
        
        self.url_blacklist_patterns = [
            r"^chrome://", 
            r"^about:", 
            r"localhost", 
            r"127\.0\.0\.1",
            r"/login", r"/signin", r"/signup",
            r"/cart", r"/checkout",
            r"/account", r"/settings",
            r"google\.com/search",
            r"youtube\.com/results",
        ]
        self.title_blacklist = [
            "404", "not found", "access denied", "error", 
            "login", "sign in", "redirecting", "loading"
        ]

    def _is_url_ignored(self, url: str) -> bool:
        """Швидка перевірка URL через Regex"""
        for pattern in self.url_blacklist_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def _is_content_empty(self, title: str, text: str) -> bool:
        """Перевірка на занадто короткий контент або помилки"""
        if not text or len(text.strip()) < 50:
            return True
        
        lower_title = (title or "").lower()
        if any(bad_word in lower_title for bad_word in self.title_blacklist):
            return True
            
        return False

    def _ai_validate(self, title: str, text: str) -> Tuple[bool, str]:
        """
        Запитуємо Ollama, чи підходить ця сторінка для рекомендацій.
        Повертає (is_valid, reason).
        """
        content_sample = f"Title: {title}\nContent: {text[:1800]}"

        prompt = f"""
        Analyze the provided webpage content text.
        
        CONTEXT: The text is raw extracted data. It may start with navigation menus (Home, Login, Sign Up, Search). 
        IGNORE the navigation links at the beginning. Focus on the MAIN BODY of the page.

        GOAL: Decide if this page contains a readable article, guide, discussion, or documentation that is useful for a user.

        CRITERIA:
        - TRUE (Recommend): Coding tutorials, news, blog posts, documentation, forum discussions, product info.
        - FALSE (Discard): 
            1. JUST a Login/Sign-up form (without an article).
            2. 404 Error / Page Not Found.
            3. Captcha / Cloudflare check.
            4. Empty content or gibberish.
            5. Adult content.

        INPUT DATA:
        {content_sample}

        Return ONLY valid JSON:
        {{"is_recommendable": true/false, "reason": "brief explanation"}}
        """
        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                format='json',
                options={'temperature': 0},
                keep_alive='5m'
            )
            import json
            result = json.loads(response['message']['content'])
            return result.get("is_recommendable", False), result.get("reason", "Unknown")

        except Exception as e:
            print(f"Filtration AI Error: {e}")
            return True, "AI Error"

    def should_process(self, url: str, title: str, text: str) -> bool:
        """
        Головний метод. Повертає True, якщо сторінку треба зберігати.
        """
        if self._is_url_ignored(url):
            print(f"Filter: Dropped by URL pattern -> {url}")
            return False

        if self._is_content_empty(title, text):
            print(f"Filter: Dropped by weak content -> {url}")
            return False

        is_valid, reason = self._ai_validate(title, text)
        if not is_valid:
            print(f"Filter: Dropped by AI ({reason}) -> {url}")
            return False

        return True