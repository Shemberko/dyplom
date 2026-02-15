import os
import uuid
import random
import logging
from datetime import datetime, timedelta, timezone
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SyntheticUserGenerator:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def _get_pages_for_category(self, category_name: str) -> list:
        """Отримує всі URL сторінок заданої категорії."""
        query = """
        MATCH (p:Page)-[:IN_CATEGORY]->(c:Category)
        WHERE toLower(c.name) = toLower($cat_name)
        RETURN p.url AS url
        """
        with self.driver.session() as session:
            result = session.run(query, cat_name=category_name.strip())
            return [record["url"] for record in result]

    def _create_user_and_visits(self, user_id: str, visits_data: list):
        """Створює користувача та масово додає зв'язки VISIT."""
        query = """
        // Створюємо або знаходимо користувача
        MERGE (u:User {id: $user_id})
        ON CREATE SET u.createdAt = datetime()
        
        WITH u
        UNWIND $visits AS visit
        MATCH (p:Page {url: visit.url})
        
        // Створюємо зв'язок візиту
        MERGE (u)-[v:VISIT]->(p)
        SET v.visitedAt = [visit.visited_at],
            v.active_time = visit.active_time,
            v.source = 'synthetic_generator'
        """
        with self.driver.session() as session:
            session.run(query, user_id=user_id, visits=visits_data)

    def generate_user(self, preferences: dict) -> str:
        """
        Головний метод: приймає словник {Категорія: Відсоток}, 
        вибирає сторінки та створює зв'язки.
        """
        user_id = f"synthetic_{uuid.uuid4().hex[:8]}"
        total_visits = 0
        all_visits_data = []

        logging.info(f"Створення користувача [{user_id}]...")

        for cat_name, percentage in preferences.items():
            urls = self._get_pages_for_category(cat_name)
            
            if not urls:
                logging.warning(f"Категорію '{cat_name}' не знайдено або в ній немає сторінок. Пропускаємо.")
                continue

            target_count = int(len(urls) * (percentage / 100.0))
            if target_count == 0 and percentage > 0:
                target_count = 1

            if target_count > len(urls):
                target_count = len(urls)

            sampled_urls = random.sample(urls, target_count)
            
            for url in sampled_urls:
                random_hours_ago = random.randint(1, 24 * 7)
                visit_time = (datetime.now(timezone.utc) - timedelta(hours=random_hours_ago)).isoformat()
                
                active_time = round(random.uniform(0.5, 15.0), 1)

                all_visits_data.append({
                    "url": url,
                    "visited_at": visit_time,
                    "active_time": active_time
                })

            logging.info(f"Відібрано {target_count} сторінок з категорії '{cat_name}'.")
            total_visits += target_count

        if all_visits_data:
            self._create_user_and_visits(user_id, all_visits_data)
            logging.info(f"✅ Успішно! Користувача {user_id} пов'язано з {total_visits} сторінками.")
        else:
            logging.error("❌ Не вдалося згенерувати жодного візиту. Перевірте назви категорій.")

        return user_id

def parse_input(user_input: str) -> dict:
    """Парсить рядок виду 'Technology 70, Food 30' у словник."""
    preferences = {}
    parts = user_input.split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        try:
            cat_name, pct_str = part.rsplit(' ', 1)
            preferences[cat_name.strip()] = float(pct_str)
        except ValueError:
            logging.warning(f"Пропущено невірний формат: '{part}'. Очікується 'НазваВідсоток' (напр., Technology 50).")
    return preferences

def main():
    generator = SyntheticUserGenerator()
    
    print("\n" + "="*50)
    print("🤖 ГЕНЕРАТОР СИНТЕТИЧНИХ КОРИСТУВАЧІВ")
    print("="*50)
    print("Введіть категорії та відсоток бази, з якими треба пов'язати юзера.")
    print("Формат: Назва Категорії Відсоток (декілька через кому).")
    print("Приклад: Technology 70, Food 30, Social Media 10")
    print("Введіть 'exit' для виходу.")
    print("="*50 + "\n")

    try:
        while True:
            user_input = input("👉 Введіть налаштування: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                break
                
            preferences = parse_input(user_input)
            
            if not preferences:
                print("❌ Немає валідних категорій для обробки. Спробуйте ще раз.\n")
                continue
                
            generator.generate_user(preferences)
            print("-" * 50)
            
    except KeyboardInterrupt:
        print("\nВихід...")
    finally:
        generator.close()

if __name__ == "__main__":
    main()