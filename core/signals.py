from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Portfolio

@receiver(post_delete, sender=Portfolio)
def delete_resume_file(sender, instance, **kwargs):
    if instance.resume:
        instance.resume.delete(save=False)
