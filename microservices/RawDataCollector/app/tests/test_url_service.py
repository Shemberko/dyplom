import unittest
import sys
import os

# 1. Отримуємо шлях до поточної папки (tests) і беремо батьківську (app)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(current_dir, '..')
sys.path.append(parent_dir)

# 2. Тепер змінюємо імпорт. 
# Замість "from ..services" використовуємо абсолютний шлях від папки app:
from services.helpers.url_processor_service import UrlProcessorService
class TestUrlProcessorService(unittest.TestCase):
    
    def setUp(self):
        """Підготовка перед кожним тестом (Test Fixture)."""
        self.processor = UrlProcessorService()

    # Сценарій 1: Нормалізація (видалення utm міток)
    def test_normalize_removes_tracking_params(self):
        raw_url = "https://example.com/page?utm_source=google&id=123&fbclid=IwAR"
        expected = "https://example.com/page?id=123"
        self.assertEqual(self.processor.normalize(raw_url), expected)

    # Сценарій 2: Приведення до нижнього регістру та видалення слешів
    def test_normalize_lowercase_and_slash(self):
        raw_url = "HTTP://Example.COM/Page/"
        expected = "http://example.com/page"
        self.assertEqual(self.processor.normalize(raw_url), expected)

    # Сценарій 3: Перевірка безпеки (HTTPS)
    def test_is_secure_logic(self):
        self.assertTrue(self.processor.is_secure("https://bank.com"))
        self.assertFalse(self.processor.is_secure("http://insecure.com"))
        self.assertFalse(self.processor.is_secure("ftp://files.com"))

    # Сценарій 4: Витягування домену (Граничний випадок - URL без http://)
    def test_extract_domain_complex(self):
        self.assertEqual(self.processor.extract_domain("https://SUB.domain.com/path"), "sub.domain.com")
        # Граничний випадок: користувач ввів просто домен
        self.assertEqual(self.processor.extract_domain("my-site.org/about"), "my-site.org")

    # Сценарій 5: Обробка помилок (Exception handling)
    def test_invalid_input_raises_error(self):
        # Передаємо None або число замість рядка, щоб викликати помилку
        with self.assertRaises(ValueError):
            self.processor.normalize(12345)

if __name__ == '__main__':
    unittest.main()