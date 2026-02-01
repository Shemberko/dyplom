import requests
from bs4 import BeautifulSoup
from typing import Any, Dict, Optional, List
from urllib.parse import urljoin

class ImageFetcherService:
    def get_preview_image(self, url: str) -> Optional[str]:
        """
        Намагається завантажити сторінку і знайти Open Graph image.
        """
        headers = { 'User-Agent': 'Mozilla/5.0 (compatible; RecSysBot/1.0; +http://yoursite.com)'}
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                return urljoin(url, og_image["content"])
            
            twitter_img = soup.find("meta", name="twitter:image")
            if twitter_img and twitter_img.get("content"):
                return urljoin(url, twitter_img["content"])

            
            return None
        except Exception as e:
            print(f"Failed to fetch image for {url}: {e}")
            return None