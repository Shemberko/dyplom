"""
Тести для FeatureExtractionService — парсинг вхідних даних від Chrome Extension.
Файл: app/services/record_processing/feature_extraction_service.py

Жодних зовнішніх залежностей — вся логіка чиста Python.
"""
import json
import pytest
from app.services.record_processing.feature_extraction_service import FeatureExtractionService


def _make_body(user_id="u1", url="https://example.com/page", title="Test Page",
               text="Some long text content here", visited_at="2026-05-01T12:00:00Z",
               active_ms=None) -> bytes:
    """Генератор тестових даних у форматі Chrome Extension."""
    return json.dumps({
        "user": {"info": {"id": user_id, "email": "test@test.com"}},
        "log": [{
            "visitedAt": visited_at,
            "info": {
                "url": url,
                "title": title,
                "metaDescription": "desc",
                "textSample": text,
                "previewImage": None,
                "active": active_ms,
                "totalOpen": None,
            }
        }]
    }).encode("utf-8")


@pytest.fixture
def svc():
    return FeatureExtractionService()


# ---------------------------------------------------------------------------
# parse_and_extract
# ---------------------------------------------------------------------------

class TestParseAndExtract:

    def test_returns_user_id_and_entries(self, svc):
        """Результат містить user_id і список entries."""
        result = svc.parse_and_extract(_make_body())
        assert result["user_id"] == "u1"
        assert len(result["entries"]) == 1

    def test_entry_has_canonical_url(self, svc):
        """Кожен запис має canonical_url (нормалізований)."""
        result = svc.parse_and_extract(_make_body())
        entry = result["entries"][0]
        assert "canonical_url" in entry
        assert entry["canonical_url"].startswith("https://")

    def test_entry_has_raw_url(self, svc):
        """Кожен запис зберігає оригінальний raw_url."""
        result = svc.parse_and_extract(_make_body(url="https://example.com/page?utm_source=x"))
        entry = result["entries"][0]
        assert entry["raw_url"] == "https://example.com/page?utm_source=x"

    def test_active_time_converted_to_minutes(self, svc):
        """active_time_mins = active_ms / 60000."""
        result = svc.parse_and_extract(_make_body(active_ms=120000))
        entry = result["entries"][0]
        assert entry["active_time_mins"] == pytest.approx(2.0)

    def test_active_time_none_when_missing(self, svc):
        """Якщо active відсутнє → active_time_mins == None."""
        result = svc.parse_and_extract(_make_body(active_ms=None))
        assert result["entries"][0]["active_time_mins"] is None

    def test_skips_entry_without_url(self, svc):
        """Запис без url пропускається."""
        body = json.dumps({
            "user": {"info": {"id": "u1"}},
            "log": [{"visitedAt": "2026-01-01", "info": {"title": "No URL"}}]
        }).encode()
        result = svc.parse_and_extract(body)
        assert result["entries"] == []

    def test_returns_none_for_invalid_json(self, svc):
        """Некоректний JSON → None."""
        result = svc.parse_and_extract(b"not-json")
        assert result is None

    def test_returns_none_for_empty_bytes(self, svc):
        """Порожні байти → None."""
        result = svc.parse_and_extract(b"")
        assert result is None

    def test_returns_none_for_non_dict_json(self, svc):
        """JSON-масив (не dict) → None."""
        result = svc.parse_and_extract(b"[1, 2, 3]")
        assert result is None

    def test_double_encoded_json(self, svc):
        """Подвійно закодований JSON (рядок у рядку) теж парситься."""
        inner = json.dumps({
            "user": {"info": {"id": "u42"}},
            "log": []
        })
        body = json.dumps(inner).encode("utf-8")
        result = svc.parse_and_extract(body)
        assert result is not None
        assert result["user_id"] == "u42"

    def test_multiple_entries(self, svc):
        """Кілька записів у log — всі обробляються."""
        body = json.dumps({
            "user": {"info": {"id": "u1"}},
            "log": [
                {"visitedAt": "2026-05-01", "info": {"url": f"https://site{i}.com", "title": f"Page {i}"}}
                for i in range(3)
            ]
        }).encode()
        result = svc.parse_and_extract(body)
        assert len(result["entries"]) == 3


# ---------------------------------------------------------------------------
# _build_text_sample (внутрішній метод)
# ---------------------------------------------------------------------------

class TestBuildTextSample:

    def test_combines_title_description_sample(self, svc):
        """Всі три поля об'єднуються через подвійний перенос рядка."""
        info = {"title": "Title", "metaDescription": "Desc", "textSample": "Sample"}
        result = svc._build_text_sample(info)
        assert "Title" in result
        assert "Desc" in result
        assert "Sample" in result
        assert "\n\n" in result

    def test_skips_empty_fields(self, svc):
        """Порожні поля пропускаються."""
        info = {"title": "Only Title", "metaDescription": "", "textSample": None}
        result = svc._build_text_sample(info)
        assert result == "Only Title"

    def test_all_empty_returns_empty_string(self, svc):
        """Усі поля порожні → порожній рядок."""
        result = svc._build_text_sample({})
        assert result == ""
