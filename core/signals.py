import httpx
import logging

from django.conf import settings
from django.dispatch import receiver
from allauth.account.signals import user_logged_in
from allauth.socialaccount.models import SocialAccount

logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def populate_supabase_profile(sender, request, user, **kwargs):
    logger.info("user_logged_in SIGNAL triggered")
    logger.info(f"User ID: {user.id}")

    # Attempt to get email from user model
    email = user.email or ''
    logger.info(f"User Model Email: {email}")

    # Fallback: try to get email from social account
    try:
        social_email = SocialAccount.objects.get(user=user).extra_data.get("email", "")
        logger.info(f"Fallback Email from SocialAccount: {social_email}")
    except SocialAccount.DoesNotExist:
        social_email = ""
        logger.warning("No SocialAccount found for this user")

    SUPABASE_URL = "https://qdlguxijkkuujnaeuhqq.supabase.co"
    SUPABASE_API_KEY = settings.SUPABASE_SERVICE_ROLE_KEY

    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    }

    # Step 1: Check if the user already has a portfolio entry
    try:
        params = {"user_id": f"eq.{user.id}"}
        res = httpx.get(f"{SUPABASE_URL}/rest/v1/portfolios", headers=headers, params=params)
        logger.info(f"Supabase fetch status: {res.status_code}")
        logger.info(f"Supabase fetch response: {res.text}")
    except Exception as e:
        logger.error(f"Error fetching user portfolio from Supabase: {e}")
        return

    # Step 2: Create or patch entry
    if res.status_code == 200:
        data = res.json()
        if not data:
            # No row exists — insert a new one
            payload = {
                "user_id": user.id,
                "email": email or social_email,
                "name": user.get_full_name() or "",
            }
            try:
                post_res = httpx.post(f"{SUPABASE_URL}/rest/v1/portfolios", headers=headers, json=payload)
                logger.info(f"Supabase POST result: {post_res.status_code} - {post_res.text}")
            except Exception as e:
                logger.error(f"Error creating new user portfolio in Supabase: {e}")
        else:
            # Row exists — patch email if missing
            existing = data[0]
            if not existing.get("email"):
                patch_payload = {
                    "email": email or social_email
                }
                try:
                    patch_res = httpx.patch(
                        f"{SUPABASE_URL}/rest/v1/portfolios?user_id=eq.{user.id}",
                        headers=headers,
                        json=patch_payload
                    )
                    logger.info(f"Supabase PATCH result: {patch_res.status_code} - {patch_res.text}")
                except Exception as e:
                    logger.error(f"Error patching email in Supabase: {e}")
