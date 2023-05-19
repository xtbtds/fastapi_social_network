from celery import Celery
from celery.schedules import crontab

app = Celery('backup_celery',
             include=['backup_celery.backup_task', 
                      'backup_celery.maintenance_task',
                      ])
app.config_from_object('backup_celery.celeryconfig')



app.conf.beat_schedule = {
    "run-me-every-ten-seconds": {
        "task": "backup_celery.backup_task.check",
        "schedule": 60.0
    }
}