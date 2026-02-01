import os
from celery import Celery

broker_url = os.environ.get("CELERY_BROKER_URL", 'amqp://guest:guest@rabbitmq/')
backend_url = os.environ.get("CELERY_BACKEND_URL", 'redis://redis:6379/0')

app = Celery('recommendation_app',
             broker=broker_url,
             backend=backend_url,
             include=['services.asyn.tasks.hybrid_embeddings']) 

app.conf.update(
    task_default_queue='default',
    beat_schedule={
        'run-gds-graphSAGE-hourly': {
            'task': 'services.asyn.tasks.hybrid_embeddings.task_build_graph_and_update_user',
            'schedule':  100.0,
        },
    },
    timezone='Europe/Kyiv'
)