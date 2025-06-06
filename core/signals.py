from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import Portfolio

@receiver(post_delete, sender=Portfolio)
def delete_resume_file(sender, instance, **kwargs):
    if instance.resume:
        instance.resume.delete(save=False)

@receiver(pre_save, sender=Portfolio)
def delete_old_resume_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return  # New portfolio, nothing to compare

    try:
        old_instance = Portfolio.objects.get(pk=instance.pk)
    except Portfolio.DoesNotExist:
        return

    # If a new file has been uploaded and it's different from the old one
    if old_instance.resume and old_instance.resume != instance.resume:
        old_instance.resume.delete(save=False)
