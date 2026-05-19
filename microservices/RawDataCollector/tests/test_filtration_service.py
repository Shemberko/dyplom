"""
Тести для FiltrationService — Regex/контент фільтрація та AI-валідація.
Файл: app/services/ai/filtration_service.py

Ollama патчиться через conftest.py (scope=session).
В тестах _ai_validate мокується на рівні instance.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.ai.filtration_service import FiltrationService


@pytest.fixture
def svc():
    """FiltrationService з підміненим Ollama Client."""
    with patch("app.services.ai.filtration_service.Client") as mock_client_cls:
        mock_client_cls.return_value = MagicMock()
        service = FiltrationService()
    return service


# ---------------------------------------------------------------------------
# _is_url_ignored
# ---------------------------------------------------------------------------

class TestIsUrlIgnored:

    def test_chrome_url_is_ignored(self, svc):
        assert svc._is_url_ignored("chrome://settings/") is True

    def test_localhost_is_ignored(self, svc):
        assert svc._is_url_ignored("http://localhost:3000/app") is True

    def test_ip_127_is_ignored(self, svc):
        assert svc._is_url_ignored("http://127.0.0.1/page") is True

    def test_login_path_is_ignored(self, svc):
        assert svc._is_url_ignored("https://example.com/login") is True

    def test_google_search_is_ignored(self, svc):
        assert svc._is_url_ignored("https://google.com/search?q=test") is True

    def test_youtube_results_is_ignored(self, svc):
        assert svc._is_url_ignored("https://youtube.com/results?search_query=cats") is True

    def test_cart_path_is_ignored(self, svc):
        assert svc._is_url_ignored("https://shop.com/cart") is True

    def test_normal_article_url_is_not_ignored(self, svc):
        assert svc._is_url_ignored("https://news.example.com/article/some-topic") is False

    def test_about_protocol_is_ignored(self, svc):
        assert svc._is_url_ignored("about:blank") is True


# ---------------------------------------------------------------------------
# _is_content_empty
# ---------------------------------------------------------------------------

class TestIsContentEmpty:

    def test_short_text_is_empty(self, svc):
        """Текст менше 50 символів → True."""
        assert svc._is_content_empty("Title", "short") is True

    def test_none_text_is_empty(self, svc):
        assert svc._is_content_empty("Title", None) is True

    def test_error_title_is_empty(self, svc):
        """Заголовок зі словом '404' → True."""
        assert svc._is_content_empty("404 Not Found", "a" * 100) is True

    def test_login_title_is_empty(self, svc):
        assert svc._is_content_empty("Login to your account", "a" * 100) is True

    def test_valid_content_not_empty(self, svc):
        """Нормальний заголовок і довгий текст → False."""
        assert svc._is_content_empty("Python Tutorial", "x" * 200) is False


# ---------------------------------------------------------------------------
# should_process — головний метод
# ---------------------------------------------------------------------------

class TestShouldProcess:

    def test_drops_chrome_url(self, svc):
        """chrome:// → False без AI-виклику."""
        result = svc.should_process("chrome://newtab", "New Tab", "x" * 100)
        assert result is False

    def test_drops_short_content(self, svc):
        """Текст < 50 символів → False без AI."""
        result = svc.should_process("https://example.com/article", "Title", "short")
        assert result is False

    def test_keeps_valid_content_when_ai_approves(self, svc):
        """AI повертає is_recommendable=True → True."""
        svc._ai_validate = MagicMock(return_value=(True, "Article"))
        result = svc.should_process(
            "https://example.com/article",
            "Great Python Tutorial",
            "x" * 200
        )
        assert result is True
        svc._ai_validate.assert_called_once()

    def test_drops_content_when_ai_rejects(self, svc):
        """AI повертає is_recommendable=False → False."""
        svc._ai_validate = MagicMock(return_value=(False, "Login page"))
        result = svc.should_process(
            "https://example.com/some-page",
            "Welcome",
            "Please sign in to continue " * 5
        )
        assert result is False

    def test_ai_error_defaults_to_keep(self, svc):
        """
        При помилці AI (_ai_validate повертає True, 'AI Error') →
        стратегія «зберегти при помилці», тому should_process → True.
        """
        svc._ai_validate = MagicMock(return_value=(True, "AI Error"))
        result = svc.should_process(
            "https://example.com/article",
            "Article Title",
            "Long content " * 20
        )
        assert result is True


# ---------------------------------------------------------------------------
# _ai_validate — мокування Ollama відповіді
# ---------------------------------------------------------------------------

class TestAiValidate:

    def test_valid_ollama_response_returns_true(self):
        """Якщо Ollama повертає is_recommendable=true → (True, reason)."""
        with patch("app.services.ai.filtration_service.Client") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.chat.return_value = {
                "message": {"content": '{"is_recommendable": true, "reason": "Article"}'}
            }
            mock_cls.return_value = mock_instance
            svc = FiltrationService()

        result, reason = svc._ai_validate("Article Title", "Long text content here.")
        assert result is True
        assert reason == "Article"

    def test_invalid_ollama_response_returns_false(self):
        """is_recommendable=false → (False, reason)."""
        with patch("app.services.ai.filtration_service.Client") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.chat.return_value = {
                "message": {"content": '{"is_recommendable": false, "reason": "Login page"}'}
            }
            mock_cls.return_value = mock_instance
            svc = FiltrationService()

        result, reason = svc._ai_validate("Login", "Please sign in.")
        assert result is False

    def test_ollama_exception_returns_true(self):
        """Виняток при виклику Ollama → (True, 'AI Error') — стратегія збереження."""
        with patch("app.services.ai.filtration_service.Client") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.chat.side_effect = Exception("Connection refused")
            mock_cls.return_value = mock_instance
            svc = FiltrationService()

        result, reason = svc._ai_validate("Title", "Content here...")
        assert result is True
        assert reason == "AI Error"
