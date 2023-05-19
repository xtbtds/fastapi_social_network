from backup_celery.celery import app
from email_core.emails import send_notification
import asyncio

async def async_tasks_for_all_users(list_of_emails):
    tasks = []
    for email in list_of_emails:
        task = asyncio.create_task(send_notification(email=email))
        tasks.append(task)
    await asyncio.gather(*tasks)


@app.task(name="task_send_notification")
def task_send_notification(emails):
    return asyncio.run(async_tasks_for_all_users(list_of_emails=emails))
