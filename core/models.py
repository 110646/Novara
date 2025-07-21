from django.db import models
from django.contrib.auth.models import User
    
class EmailCredit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    count = models.IntegerField()
    purchased_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.count} credits"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    tos_accepted = models.BooleanField(default=False)
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

class SentEmailEvent(models.Model):
    email = models.EmailField()
    event_type = models.CharField(max_length=50)
    timestamp = models.DateTimeField()
    smtp_id = models.CharField(max_length=255, blank=True)
    user_agent = models.TextField(blank=True)
    response = models.TextField(blank=True)
    custom_args = models.JSONField(null=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.email} - {self.event_type} at {self.timestamp}"

class SentEmailRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    professor_email = models.EmailField()
    university = models.CharField(max_length=255)
    date_sent = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default='Delivered')  # or 'Opened'
    email_body = models.TextField()

    smtp_id = models.CharField(max_length=255, blank=True, null=True)  # for linking with Postmark events

    def __str__(self):
        return f"{self.professor_email} - {self.status} at {self.date_sent}"