from django.db import models
from django.contrib.auth.models import User
from storages.backends.s3boto3 import S3Boto3Storage  # <-- Add this

class Portfolio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, null=True)
    major = models.CharField(max_length=255)
    class_year = models.CharField(max_length=50)
    university = models.CharField(max_length=255)
    research_interests = models.TextField(max_length=1000)

    resume = models.FileField(
        upload_to='resumes/',
        storage=S3Boto3Storage(),  # <-- Force S3/R2 usage here
        blank=True,
        null=True
    )

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        try:
            this = Portfolio.objects.get(pk=self.pk)
            if this.resume and this.resume != self.resume:
                this.resume.delete(save=False)
        except Portfolio.DoesNotExist:
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name or self.user.username}'s Portfolio"
    
class EmailCredit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    count = models.IntegerField()
    purchased_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.count} credits"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    # Add other fields as needed

    def get_profile_image(self):
        if self.image:
            return self.image.url
        # If using social auth:
        social = self.user.socialaccount_set.first()
        if social:
            return social.get_avatar_url()
        # Fallback to Gravatar
        import hashlib
        email = self.user.email.lower().encode('utf-8')
        gravatar_hash = hashlib.md5(email).hexdigest()
        return f"https://www.gravatar.com/avatar/{gravatar_hash}?d=identicon"
