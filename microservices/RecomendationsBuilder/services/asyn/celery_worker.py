import os
from celery import Celery

broker_url = os.environ.get("CELERY_BROKER_URL", 'amqp://guest:guest@rabbitmq/')
# BACKEND (Redis)
backend_url = os.environ.get("CELERY_BACKEND_URL", 'redis://redis:6379/0')

app = Celery('recommendation_app',
             broker=broker_url,
             backend=backend_url, # ВИКОРИСТОВУЄМО REDIS ДЛЯ BACKEND
             include=['services.asyn.tasks']) 

app.conf.update(
    beat_schedule={
        'run-gds-node2vec-hourly': {
            'task': 'services.asyn.tasks.run_gds_node2vec',
            'schedule':  100.0,
        },
        'aggregate-user-profiles-30m': {
            'task': 'services.asyn.tasks.trigger_user_profile_updates',
            'schedule': 100.0,
        },
        'drop-gds-projection-daily': {
            'task': 'services.asyn.tasks.drop_gds_projection',
            'schedule':  100.0,
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