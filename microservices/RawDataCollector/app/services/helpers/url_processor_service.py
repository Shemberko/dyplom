from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

class UrlProcessorService:
    """
    Клас-сервіс для обробки та нормалізації URL.
    """
    
    # Список параметрів, які зазвичай видаляються (відстеження, сесії тощо)
    PARAMS_TO_REMOVE = [
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'msclkid', '_ga',
    ]

    def __init__(self):
        """
        Конструктор сервісу.
        Можна використовувати для завантаження конфігурації, якщо потрібно.
        """
        # У цьому простому випадку конфігурація не потрібна
        pass

    def normalize(self, url: str) -> str:
        """
        Основний метод, який приймає URL у вигляді рядка (стрічки)
        і повертає його нормалізовану версію.
        """
        try:
            # 1. Розбираємо URL
            parsed_url = urlparse(url)
            
            # 2. Отримуємо параметри запиту
            query_params = parse_qs(parsed_url.query)
            
            # 3. Фільтруємо параметри
            filtered_params = {
                key: value for key, value in query_params.items()
                if key.lower() not in self.PARAMS_TO_REMOVE
            }
            
            # 4. Сортуємо для узгодженості
            sorted_params = sorted(filtered_params.items())
            
            # 5. Кодуємо назад у рядок
            new_query_string = urlencode(sorted_params, doseq=True)
            
            # 6. Збираємо URL
            normalized = parsed_url._replace(
                scheme=parsed_url.scheme.lower(),
                netloc=parsed_url.netloc.lower(),
                query=new_query_string,
                params='',      # Видаляємо параметри шляху
                fragment=''   # Видаляємо "якір" (#)
            )
            
            return urlunparse(normalized)
            
        except Exception as e:
            # Обробка випадків, коли передано некоректний URL
            print(f"Помилка нормалізації '{url}': {e}")
            # Повертаємо None або кидаємо виняток, щоб API міг це обробити
            raise ValueError(f"Не вдалося обробити URL: {e}")

