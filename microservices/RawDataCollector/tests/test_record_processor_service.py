"""
Тести для RecordProcessorService — оркестратор обробки запису.
Файл: app/services/record_processing/record_processor_service.py

Стратегія: патчимо ВСІ залежності (HistoryService, EmbeddingsService,
FiltrationService, CategorizationService, ImageFetcherService) на рівні
конструктора через MagicMock.
"""
import pytest
from unittest.mock import MagicMock, patch


def _make_service():
    """
    Створює RecordProcessorService із замоканими залежностями.
    Патчимо конструктори залежних класів, щоб уникнути реальних підключень.
    """
    with (
        patch("app.services.record_processing.record_processor_service.HistoryService"),
        patch("app.services.record_processing.record_processor_service.EmbeddingsService"),
        patch("app.services.record_processing.record_processor_service.FiltrationService"),
        patch("app.services.record_processing.record_processor_service.CategorizationService"),
        patch("app.services.record_processing.record_processor_service.ImageFetcherService"),
    ):
        from app.services.record_processing.record_processor_service import RecordProcessorService
        svc = RecordProcessorService()

    # Підміняємо всі залежності вручну (після створення)
    svc.history = MagicMock()
    svc.embeddings = MagicMock(return_value=[0.1] * 384)
    svc.filtration = MagicMock()
    svc.categorization = MagicMock()
    svc.image_fetcher = MagicMock()

    return svc


@pytest.fixture
def svc():
    return _make_service()


# ---------------------------------------------------------------------------
# process — рівень оркестрації
# ---------------------------------------------------------------------------

class TestProcess:

    def test_creates_user_when_email_present(self, svc):
        """Якщо є user_id і email → create_or_update_user викликається."""
        svc.history.page_exists.return_value = True
        data = {
            "user_id": "u1",
            "user_email": "user@test.com",
            "entries": []
        }
        svc.process(data)
        svc.history.create_or_update_user.assert_called_once_with("u1", {"email": "user@test.com"})

    def test_does_not_create_user_without_id(self, svc):
        """Якщо user_id відсутній → create_or_update_user НЕ викликається."""
        data = {"user_id": None, "entries": []}
        svc.process(data)
        svc.history.create_or_update_user.assert_not_called()

    def test_processes_each_entry(self, svc):
        """Кожен entry в списку викликає _process_single_entry."""
        svc.history.page_exists.return_value = True
        entries = [
            {"raw_url": "https://a.com", "canonical_url": "https://a.com", "title": "A"},
            {"raw_url": "https://b.com", "canonical_url": "https://b.com", "title": "B"},
        ]
        svc.process({"user_id": "u1", "entries": entries})
        assert svc.history.page_exists.call_count == 2

    def test_skips_entry_without_canonical_url(self, svc):
        """Entry без canonical_url пропускається."""
        entries = [{"raw_url": "https://a.com", "canonical_url": None}]
        svc.process({"user_id": "u1", "entries": entries})
        svc.history.page_exists.assert_not_called()

    def test_skips_entry_without_raw_url(self, svc):
        """Entry без raw_url пропускається."""
        entries = [{"raw_url": None, "canonical_url": "https://a.com"}]
        svc.process({"user_id": "u1", "entries": entries})
        svc.history.page_exists.assert_not_called()


# ---------------------------------------------------------------------------
# _process_single_entry — обробка існуючої сторінки
# ---------------------------------------------------------------------------

class TestProcessExistingPage:

    def test_updates_existing_page_without_ai(self, svc):
        """Якщо сторінка вже існує → create_or_update_page без AI-виклику."""
        svc.history.page_exists.return_value = True
        entry = {
            "raw_url": "https://a.com",
            "canonical_url": "https://a.com",
            "title": "A",
            "text_content": "Some content",
            "meta_description": "desc",
            "image_url": None,
        }
        svc._process_single_entry("u1", entry)

        svc.history.create_or_update_page.assert_called_once()
        svc.filtration.should_process.assert_not_called()
        svc.categorization.categorize.assert_not_called()

    def test_creates_visit_for_existing_page(self, svc):
        """Навіть для існуючої сторінки → create_or_update_visit викликається."""
        svc.history.page_exists.return_value = True
        entry = {
            "raw_url": "https://a.com",
            "canonical_url": "https://a.com",
            "title": "A", "text_content": "x", "meta_description": "",
        }
        svc._process_single_entry("u1", entry)
        svc.history.create_or_update_visit.assert_called_once()


# ---------------------------------------------------------------------------
# _process_single_entry — обробка нової сторінки
# ---------------------------------------------------------------------------

class TestProcessNewPage:

    def test_filters_new_page_via_filtration(self, svc):
        """Нова сторінка перевіряється через FiltrationService."""
        svc.history.page_exists.return_value = False
        svc.filtration.should_process.return_value = True
        svc.history.get_categories.return_value = []
        svc.categorization.categorize.return_value = {
            "categories": ["Technology"],
            "summary": "A great article about Python."
        }
        svc.embeddings.return_value = [0.1] * 384

        entry = {
            "raw_url": "https://new.com/article",
            "canonical_url": "https://new.com/article",
            "title": "Python Article",
            "text_content": "x" * 100,
            "meta_description": "desc",
            "image_url": None,
        }
        svc._process_single_entry("u1", entry)

        svc.filtration.should_process.assert_called_once()
        svc.categorization.categorize.assert_called_once()
        svc.history.create_or_update_page.assert_called_once()

    def test_skips_new_page_rejected_by_filtration(self, svc):
        """Нова сторінка відхилена FiltrationService → не зберігається."""
        svc.history.page_exists.return_value = False
        svc.filtration.should_process.return_value = False

        entry = {
            "raw_url": "https://spam.com",
            "canonical_url": "https://spam.com",
            "title": "Login",
            "text_content": "Please sign in.",
            "meta_description": "",
        }
        svc._process_single_entry("u1", entry)

        svc.categorization.categorize.assert_not_called()
        svc.history.create_or_update_page.assert_not_called()

    def test_uses_image_fetcher_when_no_image_url(self, svc):
        """Якщо image_url відсутній → image_fetcher.get_preview_image викликається."""
        svc.history.page_exists.return_value = False
        svc.filtration.should_process.return_value = True
        svc.history.get_categories.return_value = []
        svc.categorization.categorize.return_value = {
            "categories": ["Tech"], "summary": "Long summary here"
        }
        svc.image_fetcher.get_preview_image.return_value = "https://img.example.com/og.jpg"
        svc.embeddings.return_value = [0.1] * 384

        entry = {
            "raw_url": "https://new.com/article",
            "canonical_url": "https://new.com/article",
            "title": "Title",
            "text_content": "x" * 100,
            "meta_description": "desc",
            "image_url": None,  # ← немає зображення
        }
        svc._process_single_entry("u1", entry)

        svc.image_fetcher.get_preview_image.assert_called_once_with("https://new.com/article")

    def test_skips_image_fetcher_when_image_exists(self, svc):
        """Якщо image_url є → image_fetcher НЕ викликається."""
        svc.history.page_exists.return_value = False
        svc.filtration.should_process.return_value = True
        svc.history.get_categories.return_value = []
        svc.categorization.categorize.return_value = {
            "categories": ["Tech"], "summary": "Summary"
        }
        svc.embeddings.return_value = [0.1] * 384

        entry = {
            "raw_url": "https://new.com/article",
            "canonical_url": "https://new.com/article",
            "title": "Title",
            "text_content": "x" * 100,
            "meta_description": "desc",
            "image_url": "https://img.example.com/photo.jpg",  # ← є зображення
        }
        svc._process_single_entry("u1", entry)

        svc.image_fetcher.get_preview_image.assert_not_called()
