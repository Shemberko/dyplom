import os
import traceback
from dotenv import load_dotenv

# --- [ВИПРАВЛЕННЯ 1: ЛОГІКА sys.path] ---
# Ми додаємо до шляху 'microservices', щоб усі імпорти
# були абсолютними від цього кореня (напр., 'RecomendationsBuilder.services...')
import sys
import pathlib
# CURRENT_DIR = pathlib.Path(__file__).resolve().parent # .../RecomendationsBuilder
# MICROSERVICES_DIR = CURRENT_DIR.parent # .../microservices
# sys.path.append(str(MICROSERVICES_DIR))
# print(f"--- Додано до sys.path: {MICROSERVICES_DIR}")
# --- [КІНЕЦЬ ВИПРАВЛЕННЯ] ---


print("--- [Тестовий Скрипт Запущено] ---")

# --- Крок 1: Завантаження .env файлу ---
print("... Крок 1: Завантаження .env файлу ...")
try:
    if load_dotenv():
        print("OK: .env файл завантажено.")
    else:
        print("УВАГА: .env файл не знайдено.")
    
    uri = os.getenv("NEO4J_URI")
    print(f"OK: Знайдено URI: {uri}")
    if uri is None:
        raise ValueError("NEO4J_URI не знайдено, перевірте .env файл.")
except Exception as e:
    print(f"!!! ПОМИЛКА на Кроці 1: {e}")
    exit()

# --- Крок 2: Перевірка імпорту та neo4j_client ---
print("\n... Крок 2: Імпорт тасків та перевірка neo4j_client ...")
try:
    # --- [ВИПРАВЛЕННЯ 2: Абсолютні імпорти] ---
    # Імпортуємо ЄДИНИЙ екземпляр 'query_runner' (під псевдонімом neo4j_client),
    # який використовується і в 'tasks.py'
    from services.neo4j.query_runner import query_runner as neo4j_client
    
    # Імпортуємо ТІЛЬКИ той таск, який нам потрібен для тестування
    from services.asyn.tasks import (
        run_gds_node2vec,
        incrementally_update_text_profile_from_recent,
        incrementally_update_structural_profile_from_recent
    )
    # --- [КІНЕЦЬ ВИПРАВЛЕННЯ] ---
    
    print("OK: Таски успішно імпортовано.")
    
    # Використовуємо імпортований neo4j_client для перевірки з'єднання
    test_result_list = neo4j_client.run_query("RETURN 1 AS test")
    
    # run_query повертає список dict
    if test_result_list:
        print(f"OK: Тестовий запит до Neo4j повернув: {test_result_list[0]}")
    else:
        print(f"OK: Тестовий запит до Neo4j повернув: {test_result_list}")
        
    print("+++ Neo4j client ПРАЦЮЄ.")
except ImportError as e:
    print(f"!!! ПОМИЛКА ІМПОРТУ: {e}")
    print("!!! Переконайтеся, що всі імпорти у 'tasks.py' ТАКОЖ абсолютні.")
    traceback.print_exc()
    exit()
except Exception as e:
    print(f"!!! ПОМИЛКА neo4j_client: {e}")
    print("!!! Перевірте URI, пароль та чи запущена база Neo4j.")
    traceback.print_exc()
    exit()

# --- Крок 3: Виконання Тестів ---
print("\n--- Крок 3: Тестування тасків ---")

# === 1. ВСТАВТЕ ВАШІ ТЕСТОВІ ДАНІ ТУТ ===
#
#    Нам НЕ ПОТРІБЕН 'elementId' для цього тесту, 
#    але нам потрібен 'USER_ID', який має відвідування
#
TEST_USER_ID = "101776457075996230946" # <--- ID КОРИСТУВАЧА ДЛЯ ТЕСТУ
# =======================================


# --- [ВИПРАВЛЕННЯ 3: Фокус на одному тесті] ---

# === Тест 1 (Одиночний Structural) ===
print(f"\n[Teст 1] Оновлення Structural (одиночний) - ПРОПУЩЕНО.")

# === Тест 2 (Одиночний Text) ===
print(f"\n[Teст 2] Оновлення Text (одиночний) - ПРОПУЩЕНО.")

# === ГОЛОВНИЙ ТЕСТ: Пакетне інкрементальне оновлення ТЕКСТОВИХ ембедінгів ===
print(f"\n[ГОЛОВНИЙ ТЕСТ] Запуск ПАКЕТНОГО ІНКРЕМЕНТАЛЬНОГО оновлення (Text) для user '{TEST_USER_ID}' (за останні 36 годин)...")
try:
    # Викликаємо ТІЛЬКИ текстову функцію з новим параметром
    # res_recompute_t = incrementally_update_text_profile_from_recent(
    #     neo4j_client=neo4j_client,
    #     user_id=TEST_USER_ID,
    #     hours_ago=36  # <--- Як ви і просили
    # )
    # res_recompute_t = run_gds_node2vec(neo4j_client=neo4j_client)
    res_recompute_s = incrementally_update_structural_profile_from_recent(
        neo4j_client=neo4j_client, # <--- Передаємо клієнт
        user_id=TEST_USER_ID,
        hours_ago=36
    )

    print(f"+++ Результат (Batch Text): {res_recompute_s}")
    
except Exception as e:
    print(f"!!! ПОМИЛКА (Batch Update): {e}")
    traceback.print_exc()
# --- [КІНЕЦЬ ВИПРАВЛЕННЯ] ---


print("\n--- [Тестовий Скрипт Завершено] ---")