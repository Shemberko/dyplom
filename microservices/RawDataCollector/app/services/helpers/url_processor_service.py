from typing import Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, quote, unquote
import re
import logging

logger = logging.getLogger(__name__)

class UrlProcessorService:
    """
    Оптимізований сервіс для нормалізації URL:
    - використовує множину для швидкої фільтрації параметрів;
    - коректно обробляє відсутню схему, IDNA-хости, user:pass, порти;
    - декодує і повторно кодує path без втрати слешів;
    - видаляє сесійні токени у шляху;
    - детерміністично сортує ключі і значення query.
    """
    PARAMS_TO_REMOVE = {
        'utm_source','utm_medium','utm_campaign','utm_term','utm_content',
        'fbclid','gclid','msclkid','_ga'
    }

    _SESSION_RE = re.compile(r';(?:jsessionid|phpsessid|sid|session|sessid)=[^/;]*', re.I)
    _MULTI_SLASH_RE = re.compile(r'/+')

    def __init__(self, remove_www: bool = False, lower_path: bool = True):
        self.remove_www = remove_www
        self.lower_path = lower_path
        # кешована множина для прискорення перевірки
        self._params_to_remove = {p.lower() for p in self.PARAMS_TO_REMOVE}

    def normalize(self, url: str) -> str:
        if not isinstance(url, str):
            raise ValueError("URL повинен бути рядком")
        url = url.strip()
        if url == "":
            raise ValueError("Порожній URL")

        # Додати схему, якщо її нема (щоб urlparse коректно наповнив netloc)
        if '://' not in url:
            url = 'http://' + url

        try:
            parsed = urlparse(url)

            scheme = (parsed.scheme or 'http').lower()

            # hostname -> IDNA
            hostname = parsed.hostname or ''
            try:
                hostname_idna = hostname.encode('idna').decode('ascii')
            except Exception:
                hostname_idna = hostname

            if self.remove_www and hostname_idna.startswith('www.'):
                hostname_idna = hostname_idna[4:]

            # Збираємо netloc (зберігаємо user:pass при наявності)
            netloc = ''
            if parsed.username:
                netloc += parsed.username
                if parsed.password:
                    netloc += ':' + parsed.password
                netloc += '@'
            netloc += hostname_idna
            port = parsed.port
            if port and not ((scheme == 'http' and port == 80) or (scheme == 'https' and port == 443)):
                netloc += f":{port}"

            # Path: декодуємо, чистимо, стискаємо слеші, видаляємо сесійні токени
            path = parsed.path or '/'
            path = unquote(path)
            path = self._SESSION_RE.sub('', path)
            path = self._MULTI_SLASH_RE.sub('/', path)
            if path.endswith('/') and len(path) > 1:
                path = path.rstrip('/')
            if self.lower_path:
                path = path.lower()
            # Повторно кодуємо шлях, дозволяючи безпечні символи
            safe_chars = "/~:@&+$,=;%-._!~*'()"
            path = quote(path, safe=safe_chars)

            # Query: розбираємо, фільтруємо, видаляємо пусті значення, сортуємо
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            filtered = {}
            for k, vals in query_params.items():
                if k.lower() in self._params_to_remove:
                    continue
                cleaned = [v for v in vals if v != '']
                if cleaned:
                    # сорт значень для детермінізму
                    filtered[k] = sorted(cleaned)

            sorted_items = sorted(filtered.items(), key=lambda x: x[0])
            new_query = urlencode(sorted_items, doseq=True)

            normalized = parsed._replace(
                scheme=scheme,
                netloc=netloc.lower(),
                path=path,
                query=new_query,
                params='',
                fragment=''
            )
            return urlunparse(normalized)

        except Exception as e:
            logger.exception("Помилка нормалізації URL: %s", url)
            raise ValueError(f"Не вдалося обробити URL: {e}")

    def extract_domain(self, url: str) -> str:
        """
        Повертає доменне ім'я з URL.
        Наприклад: 'https://Sub.Domain.com/path' -> 'sub.domain.com'
        """
        try:
            parsed = urlparse(url)
            if not parsed.netloc and not parsed.path:
                return ""
            # Якщо urlparse не розпізнав netloc (наприклад, url без схеми), спробуємо взяти path
            domain = parsed.netloc if parsed.netloc else parsed.path.split('/')[0]
            return domain.lower()
        except Exception:
            return ""

    def is_secure(self, url: str) -> bool:
        """
        Перевіряє, чи використовує URL захищений протокол (HTTPS).
        """
        try:
            parsed = urlparse(url)
            return parsed.scheme.lower() == 'https'
        except Exception:
            return False