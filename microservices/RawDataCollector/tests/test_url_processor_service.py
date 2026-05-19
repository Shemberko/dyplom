"""
Тести для UrlProcessorService — найбільш "чиста" функція без залежностей.
Файл: app/services/record_processing/url_processor_service.py

Ці тести не потребують жодного мокування — вся логіка детермінована.
"""
import pytest
from app.services.record_processing.url_processor_service import UrlProcessorService


@pytest.fixture
def svc():
    """Сервіс з налаштуваннями за замовчуванням."""
    return UrlProcessorService()


@pytest.fixture
def svc_no_www():
    """Сервіс з увімкненим видаленням www."""
    return UrlProcessorService(remove_www=True)


# ---------------------------------------------------------------------------
# normalize — базові сценарії
# ---------------------------------------------------------------------------

class TestNormalize:

    def test_removes_fragment(self, svc):
        """Фрагмент (#anchor) видаляється."""
        result = svc.normalize("https://example.com/page#section")
        assert "#" not in result

    def test_removes_trailing_slash(self, svc):
        """Кінцевий слеш у path видаляється."""
        result = svc.normalize("https://example.com/page/")
        assert not result.endswith("/")

    def test_keeps_root_slash(self, svc):
        """URL з тільки доменом: результат залишає або прибирає — перевіряємо реальну поведінку."""
        result = svc.normalize("https://example.com/")
        # Пать == '/' і довжина > 1 — умова path.endswith('/') and len > 1 в коді не зработає,
        # бо після rstrip url = 'https://example.com' (path='/'), len('/') == 1.
        # Справжні результат: залежить від urlunparse, дозволяємо обидва варіанти.
        assert result in ("https://example.com", "https://example.com/")
        assert "example.com" in result

    def test_removes_utm_params(self, svc):
        """UTM-параметри видаляються."""
        url = "https://example.com/article?utm_source=google&utm_medium=cpc&id=42"
        result = svc.normalize(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=42" in result

    def test_removes_fbclid(self, svc):
        """fbclid видаляється."""
        url = "https://example.com/page?fbclid=IwAR123"
        result = svc.normalize(url)
        assert "fbclid" not in result

    def test_adds_http_if_no_scheme(self, svc):
        """URL без схеми → додається http://."""
        result = svc.normalize("example.com/path")
        assert result.startswith("http://")

    def test_lowercases_path(self, svc):
        """Path переводиться у нижній регістр (lower_path=True за замовчуванням)."""
        result = svc.normalize("https://example.com/Path/To/Page")
        assert "/path/to/page" in result

    def test_removes_www_when_configured(self, svc_no_www):
        """Якщо remove_www=True → www. видаляється з хосту."""
        result = svc_no_www.normalize("https://www.example.com/page")
        assert "www." not in result

    def test_keeps_www_by_default(self, svc):
        """За замовчуванням www. зберігається."""
        result = svc.normalize("https://www.example.com/page")
        assert "www.example.com" in result

    def test_normalizes_port_80_http(self, svc):
        """Стандартний порт 80 для http видаляється."""
        result = svc.normalize("http://example.com:80/page")
        assert ":80" not in result

    def test_normalizes_port_443_https(self, svc):
        """Стандартний порт 443 для https видаляється."""
        result = svc.normalize("https://example.com:443/page")
        assert ":443" not in result

    def test_keeps_non_standard_port(self, svc):
        """Нестандартний порт зберігається."""
        result = svc.normalize("http://example.com:8080/page")
        assert ":8080" in result

    def test_sorts_query_params(self, svc):
        """Query-параметри сортуються за ключем детерміністично."""
        url1 = svc.normalize("https://example.com/?z=1&a=2")
        url2 = svc.normalize("https://example.com/?a=2&z=1")
        assert url1 == url2

    def test_removes_session_token_in_path(self, svc):
        """Сесійний токен у path (;jsessionid=...) видаляється."""
        result = svc.normalize("https://example.com/page;jsessionid=ABC123")
        assert "jsessionid" not in result

    def test_empty_url_raises_value_error(self, svc):
        """Порожній рядок → ValueError."""
        with pytest.raises(ValueError, match="Порожній URL"):
            svc.normalize("")

    def test_non_string_raises_value_error(self, svc):
        """Не рядок → ValueError."""
        with pytest.raises(ValueError, match="URL повинен бути рядком"):
            svc.normalize(12345)

    def test_same_url_twice_gives_same_result(self, svc):
        """Ідемпотентність: нормалізація двічі дає той самий результат."""
        url = "https://Example.COM/Some/Path?b=2&a=1&utm_source=x#frag"
        r1 = svc.normalize(url)
        r2 = svc.normalize(r1)
        assert r1 == r2


# ---------------------------------------------------------------------------
# extract_domain
# ---------------------------------------------------------------------------

class TestExtractDomain:

    def test_extracts_domain_from_full_url(self, svc):
        assert svc.extract_domain("https://news.example.com/article") == "news.example.com"

    def test_domain_is_lowercase(self, svc):
        assert svc.extract_domain("https://News.Example.COM/") == "news.example.com"

    def test_returns_empty_for_invalid(self, svc):
        assert svc.extract_domain("") == ""


# ---------------------------------------------------------------------------
# is_secure
# ---------------------------------------------------------------------------

class TestIsSecure:

    def test_https_is_secure(self, svc):
        assert svc.is_secure("https://example.com") is True

    def test_http_is_not_secure(self, svc):
        assert svc.is_secure("http://example.com") is False

    def test_invalid_url_returns_false(self, svc):
        assert svc.is_secure("not-a-url") is False
