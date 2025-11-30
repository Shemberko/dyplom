# from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# class UrlProcessorService:
#     """
#     Клас-сервіс для обробки та нормалізації URL.
#     """
    
#     # Список параметрів, які зазвичай видаляються (відстеження, сесії тощо)
#     PARAMS_TO_REMOVE = [
#         'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
#         'fbclid', 'gclid', 'msclkid', '_ga',
#     ]

#     def __init__(self):
#         """
#         Конструктор сервісу.
#         Можна використовувати для завантаження конфігурації, якщо потрібно.
#         """
#         # У цьому простому випадку конфігурація не потрібна
#         pass

#     def normalize(self, url: str) -> str:
#         """
#         Основний метод, який приймає URL у вигляді рядка (стрічки)
#         і повертає його нормалізовану версію.
#         """
#         try:
#             # 1. Розбираємо URL
#             parsed_url = urlparse(url)
            
#             # 2. Отримуємо параметри запиту
#             query_params = parse_qs(parsed_url.query)
            
#             # 3. Фільтруємо параметри
#             filtered_params = {
#                 key: value for key, value in query_params.items()
#                 if key.lower() not in self.PARAMS_TO_REMOVE
#             }
            
#             # 4. Сортуємо для узгодженості
#             sorted_params = sorted(filtered_params.items())
            
#             # 5. Кодуємо назад у рядок
#             new_query_string = urlencode(sorted_params, doseq=True)
            
#             # 6. Збираємо URL
#             normalized = parsed_url._replace(
#                 scheme=parsed_url.scheme.lower(),
#                 netloc=parsed_url.netloc.lower(),
#                 query=new_query_string,
#                 params='',      # Видаляємо параметри шляху
#                 fragment=''   # Видаляємо "якір" (#)
#             )
            
#             return urlunparse(normalized)
            
#         except Exception as e:
#             # Обробка випадків, коли передано некоректний URL
#             print(f"Помилка нормалізації '{url}': {e}")
#             # Повертаємо None або кидаємо виняток, щоб API міг це обробити
#             raise ValueError(f"Не вдалося обробити URL: {e}")


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

    # Додатковий список параметрів, значення яких потрібно узагальнити (наприклад, замінити на плейсхолдер)
    # Якщо потрібно узагальнення значень (як обговорювалося), додайте їх сюди.
    # Наразі залишаємо цей список порожнім, оскільки ви просили лише про канонізацію.
    # PARAMS_TO_GENERALIZE = ['product_id', 'user_id', 'session_id'] 

    def __init__(self):
        """
        Конструктор сервісу.
        """
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
            
            # 3. Фільтруємо параметри (видалення)
            filtered_params = {
                key: value for key, value in query_params.items()
                if key.lower() not in self.PARAMS_TO_REMOVE
            }
            
            # 4. Сортуємо для узгодженості
            sorted_params = sorted(filtered_params.items())
            
            # 5. Кодуємо назад у рядок запиту
            new_query_string = urlencode(sorted_params, doseq=True)

            # ----------------------------------------------------
            # 6. ПОКРАЩЕННЯ КАНОНІЗАЦІЇ (Нова логіка)
            # ----------------------------------------------------

            # Нормалізація шляху:
            normalized_path = parsed_url.path
            
            # A. Видаляємо кінцеву скісну риску (trailing slash) для узагальнення:
            # Це перетворює '/page/' на '/page', але залишає '/' як '/'
            if normalized_path.endswith('/') and len(normalized_path) > 1:
                normalized_path = normalized_path.rstrip('/')

            # B. Приводимо шлях до нижнього регістру:
            normalized_path = normalized_path.lower()
            
            # 7. Збираємо URL, застосовуючи всі правила нормалізації
            normalized = parsed_url._replace(
                scheme=parsed_url.scheme.lower(),      # Схема до нижнього регістру (http/https)
                netloc=parsed_url.netloc.lower(),      # Домен до нижнього регістру
                path=normalized_path,                  # Використовуємо нормалізований шлях
                query=new_query_string,                # Використовуємо відфільтрований та відсортований запит
                params='',                             # Видаляємо параметри шляху (як і раніше)
                fragment=''                            # Видаляємо "якір" (#) (як і раніше)
            )
            
            return urlunparse(normalized)
            
        except Exception as e:
            # Обробка випадків, коли передано некоректний URL
            print(f"Помилка нормалізації '{url}': {e}")
            raise ValueError(f"Не вдалося обробити URL: {e}")