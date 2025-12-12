import os
from celery import Celery

# Читаємо URL брокера з змінних середовища Docker Compose
broker_url = os.environ.get("CELERY_BROKER_URL", 'redis://redis:6379/0')

app = Celery('recommendation_app',
             broker=broker_url,
             backend=broker_url,
             # Вказуємо шлях до завдань
             include=['services.asyn.tasks']) 

# Конфігурація для Celery Beat
app.conf.update(
    beat_schedule={
        # 1. Завдання GNN (Структурні Ембедінги Сторінок)
        'run-gds-node2vec-hourly': {
            # Викликає task, який не вимагає параметрів
            'task': 'services.asyn.tasks.run_gds_node2vec',
            'schedule': 3600.0,  # Раз на годину (3600 секунд)
        },
        
        # 2. Майстер-завдання для агрегації профілів (запускає підзавдання)
        'aggregate-user-profiles-30m': {
            'task': 'services.asyn.tasks.trigger_user_profile_updates',
            'schedule': 1800.0,  # Раз на 30 хвилин (1800 секунд)
        },
        
        # 3. Додаткове завдання для очищення кешу (Node2Vec створює проєкції)
        'drop-gds-projection-daily': {
            'task': 'services.asyn.tasks.drop_gds_projection',
            'schedule': 86400.0, # Раз на 24 години
        },
    },
    timezone='Europe/Kyiv'
)