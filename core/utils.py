from django.shortcuts import redirect
from functools import wraps
import httpx
import random
import traceback
from core.models import EmailCredit
from django.contrib.auth.models import User
from django.conf import settings
import boto3

SUPABASE_URL = "https://qdlguxijkkuujnaeuhqq.supabase.co"
SUPABASE_API_KEY = settings.SUPABASE_SERVICE_ROLE_KEY
OPENAI_TEMPLATE_ENDPOINT = "http://localhost:8000/generate-email-template/"


def require_google_connection(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.socialaccount_set.filter(provider='google').exists():
            return redirect('/dashboard/?google_required=1')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def send_emails_after_payment(user_id):
    try:
        user = User.objects.get(id=user_id)

        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}"
        }

        # Step 1: Get portfolio
        params = {"user_id": f"eq.{user.id}"}
        response = httpx.get(f"{SUPABASE_URL}/rest/v1/portfolios", headers=headers, params=params)
        portfolio = response.json()[0] if response.status_code == 200 and response.json() else {}

        if not portfolio:
            print("❌ No portfolio found.")
            return

        # Step 1.5: Download resume from R2
        resume_bytes = download_resume_from_r2(portfolio.get("resume_url"))
        if not resume_bytes:
            print("❌ Failed to retrieve resume for OpenAI.")
            return

        # Step 2: Send to OpenAI
        files = {
            "resume": ("resume.pdf", resume_bytes, "application/pdf")
        }
        data = {
            "name": portfolio.get("name"),
            "email": portfolio.get("email"),
            "major": portfolio.get("major"),
            "class_year": portfolio.get("class_year"),
            "university": portfolio.get("university"),
            "research_interests": portfolio.get("research_interests")
        }

        openai_res = httpx.post(OPENAI_TEMPLATE_ENDPOINT, data=data, files=files, timeout=60.0)
        if openai_res.status_code != 200:
            print("❌ OpenAI template generation failed:", openai_res.text)
            return

        template = openai_res.json().get("template")
        if not template:
            print("❌ Template missing in OpenAI response.")
            return

        # Step 3: Get latest email credit count
        email_credit = EmailCredit.objects.filter(user=user).order_by('-purchased_at').first()
        count = email_credit.count if email_credit else 0

        # Step 4: Fetch professors
        prof_params = {
            "major": f"eq.{portfolio.get('major')}",
            "select": "*"
        }
        prof_res = httpx.get(f"{SUPABASE_URL}/rest/v1/professors", headers=headers, params=prof_params)
        all_profs = prof_res.json()

        if not all_profs:
            print("❌ No professors found for major.")
            return

        random.shuffle(all_profs)
        selected_profs = all_profs[:count]

        # Step 5: Call Cloudflare Worker
        worker_payload = {
            "template": template,
            "student": data,
            "professors": selected_profs
        }

        worker_res = httpx.post(settings.CLOUDFLARE_WORKER_URL, json=worker_payload)
        print("✅ Cloudflare response:", worker_res.status_code, worker_res.text)

    except Exception:
        traceback.print_exc()


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

        bucket = settings.AWS_STORAGE_BUCKET_NAME  # should be 'resume-uploads'
        
        # Extract just the object key (skip the bucket prefix)
        parsed = urlparse(resume_url)
        raw_path = parsed.path.lstrip("/")  # remove leading slash
        key_parts = raw_path.split("/")[1:]  # skip 'resume-uploads'
        key = unquote("/".join(key_parts))  # decode %20 etc.

        print("✅ R2 object key:", key)

        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()
    except Exception as e:
        print("❌ Resume download failed:", e)
        return None


