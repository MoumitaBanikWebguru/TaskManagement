from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from .models import Task

@shared_task
def send_weekly_summary_email():
    tasks = Task.objects.filter(status="pending")
    message = "\n".join([t.title for t in tasks])
    send_mail(
        subject="Weekly Task Summary",
        message=f"Pending tasks:\n{message}",
        from_email="noreply@taskapp.com",
        recipient_list=["student@yopmail.com"],
    )
    print(f"Sent summary email at {timezone.now()}")
