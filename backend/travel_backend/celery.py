import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_backend.settings')

app = Celery('travel_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic Tasks
app.conf.beat_schedule = {
    'update-weather-data': {
        'task': 'integrations.tasks.update_weather_cache',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'update-travel-advisories': {
        'task': 'integrations.tasks.update_travel_advisories',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
    'cleanup-old-sessions': {
        'task': 'chatbot.tasks.cleanup_old_chat_sessions',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'retrain-recommendation-model': {
        'task': 'ml_models.tasks.retrain_models',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Weekly on Sunday
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')