from celery import Celery
from celery.schedules import crontab

app = Celery('crontab_tasks',
             include=['crontab_tasks.tasks'])
app.config_from_object('crontab_tasks.celeryconfig')



app.conf.beat_schedule = {
    "run-me-every-ten-seconds": {
        "task": "crontab_tasks.tasks.check",
        "schedule": 10.0
    }
}