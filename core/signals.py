from django.dispatch import receiver
from allauth.account.signals import user_logged_in
import httpx
from django.conf import settings

@receiver(user_logged_in)
def populate_supabase_profile(sender, request, user, **kwargs):
    SUPABASE_URL = "https://qdlguxijkkuujnaeuhqq.supabase.co"
    SUPABASE_API_KEY = settings.SUPABASE_SERVICE_ROLE_KEY

    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    }

    # Check if entry already exists
    params = {"user_id": f"eq.{user.id}"}
    res = httpx.get(f"{SUPABASE_URL}/rest/v1/portfolios", headers=headers, params=params)

    if res.status_code == 200 and not res.json():
        payload = {
            "user_id": user.id,
            "email": user.email,
            "name": user.get_full_name() or "",
        }
        httpx.post(f"{SUPABASE_URL}/rest/v1/portfolios", headers=headers, json=payload)
