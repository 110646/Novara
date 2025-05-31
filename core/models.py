from django.db import models
from django.contrib.auth.models import User

class Portfolio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    major = models.CharField(max_length=255)
    class_year = models.CharField(max_length=50)  # increased length for descriptive names
    university = models.CharField(max_length=255)
    goals = models.TextField(max_length=1000)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Portfolio"
