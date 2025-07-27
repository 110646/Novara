from django.shortcuts import redirect
from functools import wraps
import httpx
import random
import traceback
from core.models import EmailCredit
from django.contrib.auth.models import User
from django.conf import settings
import boto3
import logging
from core.progress_tracker import user_progress

SUPABASE_URL = "https://qdlguxijkkuujnaeuhqq.supabase.co"
SUPABASE_API_KEY = settings.SUPABASE_SERVICE_ROLE_KEY
OPENAI_TEMPLATE_ENDPOINT = "https://8de0dc7cb3b6.ngrok-free.app/generate-email-template/"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


def require_google_connection(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.socialaccount_set.filter(provider='google').exists():
            return redirect('/dashboard/?google_required=1')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def send_emails_after_payment(user_id, user_progress):
    try:
        logger.info("🔁 Starting email dispatch flow for user ID: %s", user_id)
        user_progress[user_id] = {"progress": 10, "message": "Starting email dispatch…", "complete": False}

        user = User.objects.get(id=user_id)

        headers = {"apikey": SUPABASE_API_KEY, "Authorization": f"Bearer {SUPABASE_API_KEY}"}

        logger.debug("📡 Fetching portfolio from Supabase")
        params = {"user_id": f"eq.{user.id}"}
        response = httpx.get(f"{SUPABASE_URL}/rest/v1/portfolios", headers=headers, params=params)
        portfolio = response.json()[0] if response.status_code == 200 and response.json() else {}

        if not portfolio:
            logger.error("❌ No portfolio found for user.")
            user_progress[user_id] = {"progress": 100, "message": "Failed: No portfolio found", "complete": True}
            return

        user_progress[user_id] = {"progress": 20, "message": "Portfolio fetched successfully", "complete": False}

        logger.info("📥 Downloading resume from R2")
        resume_bytes = download_resume_from_r2(portfolio.get("resume_url"))
        if not resume_bytes:
            logger.error("❌ Failed to retrieve resume for OpenAI.")
            user_progress[user_id] = {"progress": 100, "message": "Failed: Resume download error", "complete": True}
            return

        user_progress[user_id] = {"progress": 30, "message": "Resume downloaded", "complete": False}

        logger.info("📤 Sending resume and info to OpenAI for template generation")
        files = {"resume": ("resume.pdf", resume_bytes, "application/pdf")}
        data = {
            "id": user.id,
            "name": portfolio.get("name"),
            "email": portfolio.get("email"),
            "major": portfolio.get("major"),
            "class_year": portfolio.get("class_year"),
            "university": portfolio.get("university"),
            "research_interests": portfolio.get("research_interests")
        }

        openai_res = httpx.post(OPENAI_TEMPLATE_ENDPOINT, data=data, files=files, timeout=60.0)
        if openai_res.status_code != 200:
            logger.error("❌ OpenAI template generation failed: %s", openai_res.text)
            user_progress[user_id] = {"progress": 100, "message": "Failed: OpenAI generation error", "complete": True}
            return

        template = openai_res.json().get("template")
        if not template:
            logger.error("❌ No template returned from OpenAI")
            user_progress[user_id] = {"progress": 100, "message": "Failed: No template received", "complete": True}
            return

        user_progress[user_id] = {"progress": 50, "message": "Email template generated", "complete": False}

        email_credit = EmailCredit.objects.filter(user=user).order_by('-purchased_at').first()
        count = email_credit.count if email_credit else 0
        logger.info("📬 User has %d email credits", count)

        logger.debug("📡 Fetching professors from Supabase")
        prof_params = {"major": f"eq.{portfolio.get('major')}", "select": "*"}
        prof_res = httpx.get(f"{SUPABASE_URL}/rest/v1/professors", headers=headers, params=prof_params)
        all_profs = prof_res.json()

        if not all_profs:
            logger.error("❌ No professors found for major: %s", portfolio.get("major"))
            user_progress[user_id] = {"progress": 100, "message": "Failed: No professors found", "complete": True}
            return

        logger.info("📚 Found %d professors, selecting %d randomly", len(all_profs), count)
        random.shuffle(all_profs)
        selected_profs = all_profs[:count]

        user_progress[user_id] = {"progress": 60, "message": "Professors selected", "complete": False}

        logger.info("📡 Sending to Cloudflare Worker")
        worker_payload = {
            "template": template,
            "student": data,
            "professors": selected_profs
        }

        worker_res = httpx.post(settings.CLOUDFLARE_WORKER_URL, json=worker_payload)
        logger.info("✅ Cloudflare response: %s %s", worker_res.status_code, worker_res.text)

        user_progress[user_id] = {"progress": 100, "message": "Emails sent successfully!", "complete": True}

    except Exception as e:
        logger.exception("❌ Unhandled exception in send_emails_after_payment")
        user_progress[user_id] = {"progress": 100, "message": "Failed: Internal error", "complete": True}


from urllib.parse import urlparse, unquote

def download_resume_from_r2(resume_url):
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            region_name=settings.AWS_S3_REGION_NAME
        )

        bucket = settings.AWS_STORAGE_BUCKET_NAME
        
        parsed = urlparse(resume_url)
        raw_path = parsed.path.lstrip("/")
        key_parts = raw_path.split("/")[1:]
        key = unquote("/".join(key_parts))

        logger.info("✅ R2 object key: %s", key)

        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()
    except Exception as e:
        logger.exception("❌ Resume download failed")
        return None
