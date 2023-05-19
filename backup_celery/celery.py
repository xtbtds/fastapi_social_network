from celery import Celery
from celery.schedules import crontab

app = Celery('backup_celery',
             include=['backup_celery.tasks'])
app.config_from_object('backup_celery.celeryconfig')



app.conf.beat_schedule = {
    "run-me-every-ten-seconds": {
        "task": "backup_celery.tasks.check",
        "schedule": 60.0
    }
}