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
