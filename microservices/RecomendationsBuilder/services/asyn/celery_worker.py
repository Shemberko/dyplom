import os
from celery import Celery

# Читаємо URL брокера з змінних середовища Docker Compose
broker_url = os.environ.get("CELERY_BROKER_URL", 'redis://redis:6379/0')

app = Celery('recommendation_app',
             broker=broker_url,
             backend=broker_url,
             # Вказуємо шлях до завдань
             include=['services.async.tasks']) 

# Конфігурація для Celery Beat
app.conf.update(
    beat_schedule={
        'run-gds-fastrp-every-day': {
            # Шлях до функції: <файл>.<функція>
            'task': 'services.async.tasks.run_gds_fastrp',
            'schedule': 86400.0,  # Кожні 24 години
        },
    },
    timezone='Europe/Kyiv'
)