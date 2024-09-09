from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from django_apscheduler.jobstores import DjangoJobStore
from .views import send_appointment_reminders


def start():
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        send_appointment_reminders,
        'interval',
        minutes=5,
        id='send_appointment_reminders',
        replace_existing=True
    )

    scheduler.start()
