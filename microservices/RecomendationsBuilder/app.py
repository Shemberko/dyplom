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


# from services.neo4j.query_runner import query_runner as neo4j_client
# from services.asyn.tasks.structural_embeddings_building import run_gds_node2vec
# from services.asyn.tasks.structural_embeddings_aggregation import task_update_structural_profile_batch
# from services.asyn.tasks.text_embeddings_aggregation import task_update_text_profile_batch


# result = run_gds_node2vec(neo4j_client=neo4j_client)
# task_update_structural_profile_batch(
#     neo4j_client=neo4j_client,
#     user_id="101776457075996230946",
#     hours_ago=24)

# task_update_text_profile_batch(
#     neo4j_client=neo4j_client,
#     user_id="101776457075996230946",
#     hours_ago=24)