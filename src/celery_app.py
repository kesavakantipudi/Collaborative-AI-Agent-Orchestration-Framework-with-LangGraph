import os
from celery import Celery

BROKER = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/1')
BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/2')

celery = Celery('agent_app', broker=BROKER, backend=BACKEND)
celery.conf.task_routes = {'src.worker_tasks.*': {'queue': 'default'}}
celery.conf.imports = ('src.worker_tasks',)
