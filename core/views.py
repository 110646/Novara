from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.utils import require_google_connection, send_emails_after_payment
import httpx
import os
import openai
from openai import OpenAI
from django.views.decorators.http import require_POST
import urllib.parse
from django.core.files.storage import default_storage
from .models import EmailCredit, Profile, SentEmailRecord
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.utils.timezone import now
import stripe
import traceback
import json
from openai.types.chat import ChatCompletionMessageParam
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from storages.backends.s3boto3 import S3Boto3Storage
from core.choices import MAJOR_CHOICES, CLASS_YEAR_CHOICES, US_UNIVERSITY_CHOICES
from django.core.mail import send_mail
import time
from django.utils.timezone import localtime
import logging
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
from core.models import SentEmailEvent, EmailCredit, SentEmailRecord
from core.progress_tracker import user_progress
from django.urls import reverse

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY
SUPABASE_URL = "https://qdlguxijkkuujnaeuhqq.supabase.co"
SUPABASE_API_KEY = settings.SUPABASE_SERVICE_ROLE_KEY
openai.api_key = settings.OPENAI_API_KEY

# ------------------------------
# PUBLIC
# ------------------------------
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')

def custom_logout(request):
    auth_logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('home')

# ------------------------------
# DASHBOARD + PAGES
# ------------------------------
@login_required
def dashboard(request):
    user = request.user
    google_connected = user.socialaccount_set.filter(provider='google').exists()
    events = SentEmailEvent.objects.filter(user=user)
    delivered_events = events.filter(event_type="Delivery")
    total_sent = delivered_events.count()
    opened_events = events.filter(event_type="Open")
    total_opened = opened_events.count()
    open_rate = int((total_opened / total_sent) * 100) if total_sent > 0 else 0
    credits = EmailCredit.objects.filter(user=user)
    total_credits = sum(c.count for c in credits)
    context = {
        "google_connected": google_connected,
        "total_sent": total_sent,
        "total_opened": total_opened,
        "open_rate": open_rate,
        "placeholder_stat": total_credits
    }
    return render(request, "dashboard.html", context)

@never_cache
@login_required
def dashboard_stats(request):
    user = request.user
    events = SentEmailEvent.objects.filter(user=user)
    total_sent = events.filter(event_type="Delivery").count()
    total_opened = events.filter(event_type="Open").count()
    open_rate = int((total_opened / total_sent) * 100) if total_sent > 0 else 0
    return JsonResponse({
        "total_sent": total_sent,
        "total_opened": total_opened,
        "open_rate": open_rate
    })

@login_required
def sent_emails_list(request):
    emails = SentEmailRecord.objects.filter(user=request.user).order_by('-date_sent')
    data = [{
        "professor_email": email.professor_email,
        "university": email.university,
        "date_sent": localtime(email.date_sent).isoformat(),
        "status": email.status,
        "email_body": email.email_body
    } for email in emails]
    return JsonResponse(data, safe=False)

@csrf_exempt
def log_sent_email(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        professor_email = data.get('professor_email')
        university = data.get('university')
        email_body = data.get('email_body')
        smtp_id = data.get('smtp_id')
        try:
            user = User.objects.get(id=user_id)
            SentEmailRecord.objects.create(
                user=user,
                professor_email=professor_email,
                university=university,
                email_body=email_body,
                smtp_id=smtp_id,
                date_sent=timezone.now(),
            )
            return JsonResponse({'status': 'success'})
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def account(request):
    if request.method == 'POST':
        # Handle profile form submission
        user = request.user
        profile, created = Profile.objects.get_or_create(user=user)
        
        # Update user fields
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.save()
        
        # Update profile fields
        if 'profile_image' in request.FILES:
            profile.image = request.FILES['profile_image']
        
        profile.age = request.POST.get('age') or None
        profile.graduation_year = request.POST.get('graduation_year') or None
        profile.research_experience = request.POST.get('research_experience', '')
        profile.gpa = request.POST.get('gpa') or None
        profile.linkedin_url = request.POST.get('linkedin_url', '')
        profile.github_url = request.POST.get('github_url', '')
        profile.research_interests = request.POST.get('research_interests', '')
        profile.skills = request.POST.get('skills', '')
        profile.save()
        
        # Synchronize with Supabase portfolio data
        try:
            headers = {
                "apikey": SUPABASE_API_KEY,
                "Authorization": f"Bearer {SUPABASE_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Get current portfolio data
            params = {"user_id": f"eq.{user.id}"}
            response = httpx.get(f"{SUPABASE_URL}/rest/v1/portfolios", headers=headers, params=params)
            portfolio_data = response.json()[0] if response.status_code == 200 and response.json() else {}
            
            # Prepare update payload
            full_name = f"{user.first_name} {user.last_name}".strip()
            update_payload = {
                "name": full_name if full_name else user.email,
                "research_interests": profile.research_interests,
                "skills": profile.skills,
                "updated_at": now().isoformat()
            }
            
            if portfolio_data:
                # Update existing portfolio
                httpx.patch(
                    f"{SUPABASE_URL}/rest/v1/portfolios?user_id=eq.{user.id}",
                    headers=headers,
                    json=update_payload
                )
            else:
                # Create new portfolio entry
                create_payload = {
                    "user_id": int(user.id),
                    "email": user.email,
                    **update_payload
                }
                httpx.post(
                    f"{SUPABASE_URL}/rest/v1/portfolios",
                    headers=headers,
                    json=create_payload
                )
                
        except Exception as e:
            print(f"Error syncing with Supabase: {e}")
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('account')
    
    context = {}
    
    return render(request, 'account.html', context)

@login_required
def payments(request):
    payment_history = EmailCredit.objects.filter(user=request.user).order_by('-purchased_at')
    latest_payment = payment_history.first()
    total_credits = sum(c.count for c in payment_history)
    total_spent = total_credits * 0.20  # $0.20 per email
    
    context = {
        'payment_history': payment_history,
        'latest_payment': latest_payment,
        'total_credits': total_credits,
        'total_spent': total_spent,
    }
    
    return render(request, 'payments.html', context)

@login_required
def email_send_status(request):
    user_id = request.user.id
    status = user_progress.get(user_id, {
        "progress": 10,
        "message": "Initializing…",
        "complete": False
    })
    return JsonResponse(status)

# ------------------------------
# PORTFOLIO
# ------------------------------
@login_required
def portfolio(request):
    editing = request.GET.get('edit') == '1' or request.session.pop('just_created_portfolio', False)
    user = request.user
    portfolio_data = {}

    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}"
    }

    def fetch_portfolio():
        params = {"user_id": f"eq.{user.id}"}
        response = httpx.get(f"{SUPABASE_URL}/rest/v1/portfolios", headers=headers, params=params)
        return response.json()[0] if response.status_code == 200 and response.json() else {}

    try:
        portfolio_data = fetch_portfolio()
        if not portfolio_data:
            request.session['just_created_portfolio'] = True
            editing = True
    except Exception as e:
        print("Error fetching Supabase portfolio:", e)

    # Handle profile image upload
    if request.method == 'POST' and 'profile_image' in request.FILES:
        profile_image = request.FILES['profile_image']
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.image = profile_image
        profile.save()
        return redirect('portfolio')

    if request.method == 'POST':
        name = request.POST.get('name')
        major = request.POST.get('major')
        class_year = request.POST.get('class_year')
        university = request.POST.get('university')
        research_interests = request.POST.get('research_interests')
        resume_file = request.FILES.get('resume')
        resume_url = portfolio_data.get("resume_url")

        if "delete_resume" in request.POST:
            resume_url = None
            try:
                if portfolio_data.get("resume_url"):
                    from boto3 import client
                    s3 = client("s3")
                    key = portfolio_data["resume_url"].split("/")[-2] + "/" + portfolio_data["resume_url"].split("/")[-1]
                    s3.delete_object(Bucket="resume-uploads", Key=key)
            except Exception as e:
                print("Resume deletion error:", e)

        elif resume_file:
            try:
                s3_storage = S3Boto3Storage()
                path = s3_storage.save(f'resumes/{resume_file.name}', resume_file)
                resume_url = s3_storage.url(path)
                print(f"Resume uploaded to R2: {resume_url}")
            except Exception as e:
                print("Resume upload error:", e)

        payload = {
            "user_id": int(user.id),
            "name": name,
            "major": major,
            "class_year": class_year,
            "university": university,
            "research_interests": research_interests,
            "resume_url": resume_url,
            "updated_at": now().isoformat()
        }

        if user.email:
            payload["email"] = user.email

        try:
            if portfolio_data:
                res = httpx.patch(
                    f"{SUPABASE_URL}/rest/v1/portfolios?user_id=eq.{user.id}",
                    headers={**headers, "Content-Type": "application/json"},
                    json=payload
                )
            else:
                res = httpx.post(
                    f"{SUPABASE_URL}/rest/v1/portfolios",
                    headers={**headers, "Content-Type": "application/json"},
                    json=payload
                )
                
            # Synchronize with Django Profile model
            profile, created = Profile.objects.get_or_create(user=user)
            
            # Update user name if it changed
            if name and name != user.get_full_name():
                name_parts = name.split(' ', 1)
                user.first_name = name_parts[0]
                user.last_name = name_parts[1] if len(name_parts) > 1 else ''
                user.save()
            
            # Update profile fields
            profile.major = major
            profile.university = university
            profile.save()
            
        except Exception:
            traceback.print_exc()

        portfolio_data = fetch_portfolio()
        return redirect('portfolio')

    resume_filename = ""
    if portfolio_data.get("resume_url"):
        raw_name = os.path.basename(portfolio_data["resume_url"])
        resume_filename = urllib.parse.unquote(raw_name)

    def calculate_completion(portfolio):
        total = 6
        completed = sum([
        1 if portfolio.get("name") else 0,
        1 if portfolio.get("major") else 0,
        1 if portfolio.get("class_year") else 0,
        1 if portfolio.get("university") else 0,
        1 if portfolio.get("research_interests") else 0,
        1 if portfolio.get("resume_url") else 0,
    ])
        return int((completed / total) * 100)

    profile_completion = calculate_completion(portfolio_data)

    return render(request, 'portfolio.html', {
        'portfolio': portfolio_data,
        'editing': editing,
        'resume_filename': resume_filename,
        'major_choices': MAJOR_CHOICES,
        'class_year_choices': CLASS_YEAR_CHOICES,
        'university_choices': US_UNIVERSITY_CHOICES,
        'profile_completion': profile_completion,
    })

# ------------------------------
# STRIPE + EMAIL FLOW
# ------------------------------
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('metadata', {}).get('user_id')
        email_count = session.get('metadata', {}).get('email_count')

        if user_id and email_count:
            try:
                user = User.objects.get(id=user_id)
                EmailCredit.objects.create(user=user, count=int(email_count))

                # INIT user_progress here before sending emails
                user_progress[user.id] = {
                    "progress": 10,
                    "message": "Initializing...",
                    "complete": False
                }

                send_emails_after_payment(user.id, user_progress)

            except User.DoesNotExist:
                return HttpResponse(status=404)

    return HttpResponse(status=200)

@csrf_exempt
@login_required
@require_POST
def create_checkout_session(request):
    try:
        email_count = int(request.POST.get('email_count', 0))

        # 1. Validate portfolio completeness
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}"
        }
        params = {"user_id": f"eq.{request.user.id}"}
        response = httpx.get(f"{SUPABASE_URL}/rest/v1/portfolios", headers=headers, params=params)

        portfolio = response.json()[0] if response.status_code == 200 and response.json() else {}

        if not portfolio or not all([
            portfolio.get("major"),
            portfolio.get("university"),
            portfolio.get("resume_url"),
            portfolio.get("class_year"),
            portfolio.get("research_interests"),
        ]):
            return JsonResponse({'error': 'Portfolio incomplete'}, status=400)

        # 2. Calculate price and create session
        amount_cents = int(email_count * 0.20 * 100)

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Send {email_count} Emails',
                    },
                    'unit_amount': amount_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri('/emails-sent/'),
            cancel_url=request.build_absolute_uri('/send-emails/'),
            metadata={
                'user_id': str(request.user.id),
                'email_count': str(email_count)
            }
        )

        return JsonResponse({'id': session.id})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_POST
def generate_email_template(request):
    try:
        logger.info(" Starting email template generation")

        name = request.POST.get("name")
        email = request.POST.get("email")
        major = request.POST.get("major")
        university = request.POST.get("university")
        research_interests = request.POST.get("research_interests")
        class_year = request.POST.get("class_year")
        resume_file = request.FILES.get("resume")

        logger.debug(f"Form data received: name={name}, email={email}, major={major}, university={university}, class_year={class_year}, interests={research_interests}")
        if not resume_file:
            logger.warning("Resume file is missing from POST request")
            return JsonResponse({"error": "Resume file missing"}, status=400)

        prompt = f"""
You are an academic writing assistant. Write a professional cold outreach email on behalf of a student named {name}, who is majoring in {major} at {university} and expects to graduate in {class_year}. The email is being sent to a professor.

The student's resume is attached. Their stated research interests are: {research_interests}.

Your job is to generate a clear, professional, and enthusiastic email that:

Begins with: "Dear Professor {{ professor_name }}"
Expresses interest in joining the professor's research group
Highlights specific, relevant experiences or projects mentioned in the resume
Uses plain, simple, and professional language (avoid overly complex academic phrases)
Ends with a polite closing that invites further communication (e.g., asking about open opportunities)
Clearly expresses interest in joining the professor's research group
Highlights relevant accomplishments and skills from the resume
Ties their research interests and long-term goals to the professor's and student's major
Ends with a polite, actionable closing (e.g., asking about opportunities)

Format requirements:
Use ONLY these placeholders: {{ professor_name }}, {{ university }}
DO NOT invent or include any placeholders like [insert XYZ], [mention project], [describe skill], or similar. If information is missing, skip it entirely.
Any output with square brackets like [ ... ] should be considered invalid.
DO NOT include markdown, bold, or special formatting — plain text only
Keep the email 3 to 5 concise paragraphs
Make sure to indent each paragraph properly
Always end the email with this exact signature block (unless information is missing):

{name}  
{email}  

Only return the finalized email body. Do not include any explanation or commentary.
Do not include a subject line.
""".strip()

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("Connected to OpenAI")

        # Step 1: Upload resume
        logger.info("Uploading resume to OpenAI")
        file_upload = client.files.create(
            file=("resume.pdf", resume_file.read(), "application/pdf"),
            purpose="assistants"
        )
        logger.debug(f"Resume uploaded: file_id={file_upload.id}")

        # Step 2: Create thread
        thread = client.beta.threads.create()
        logger.debug(f"Thread created: thread_id={thread.id}")

        # Step 3: Add message
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=[{"type": "text", "text": prompt}],
            attachments=[{
                "file_id": file_upload.id,
                "tools": [{"type": "file_search"}]
            }]
        )
        logger.info("Prompt and resume attached to thread")

        # Step 4: Run assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=settings.OPENAI_ASSISTANT_ID,
        )
        logger.debug(f"▶Run started: run_id={run.id}")

        # Step 5: Poll for result
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            logger.debug(f"Run status: {run_status.status}")
            if run_status.status == "completed":
                logger.info(" Assistant run completed")
                break
            elif run_status.status in ["failed", "cancelled", "expired"]:
                logger.error(f" Run failed with status: {run_status.status}")
                return JsonResponse({"error": f"Run failed with status: {run_status.status}"}, status=500)
            time.sleep(2)

        # Step 6: Retrieve message
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        logger.debug(f"Retrieved {len(messages.data)} message(s)")

        latest_message = messages.data[0]
        email_template = latest_message.content[0].text.value.strip()
        logger.info("Final email template generated")

        return JsonResponse({"template": email_template})

    except Exception as e:
        logger.exception("OpenAI template generation failed")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def emails_sent_confirmation(request):
    latest_credit = EmailCredit.objects.filter(user=request.user).order_by('-purchased_at').first()
    return render(request, 'emails_sent.html', {
        'sent_count': latest_credit.count if latest_credit else 0
    })

@login_required
def send_emails_page(request):
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}"
    }
    params = {"user_id": f"eq.{request.user.id}"}
    response = httpx.get(f"{SUPABASE_URL}/rest/v1/portfolios", headers=headers, params=params)

    portfolio = response.json()[0] if response.status_code == 200 and response.json() else {}

    portfolio_complete = bool(
        portfolio and portfolio.get("major") and portfolio.get("class_year") and
        portfolio.get("university") and portfolio.get("research_interests") and portfolio.get("resume_url")
    )

    return render(request, 'send_emails.html', {
        'portfolio_complete': portfolio_complete,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY
    })



@require_POST
@csrf_exempt
def postmark_events_webhook(request):
    try:
        logger.info("📩 Postmark webhook HIT!")

        event = json.loads(request.body)
        logger.info("Received Postmark Event:\n%s", json.dumps(event, indent=2))

        metadata = event.get("Metadata", {})
        user_id = metadata.get("user_id")
        professor_id = metadata.get("professor_id")
        logger.info("Extracted metadata: user_id=%s, professor_id=%s", user_id, professor_id)

        if not user_id:
            logger.warning("Event missing user_id in metadata: %s", metadata)
            return JsonResponse({"error": "Missing user_id"}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning("No matching user found for ID: %s", user_id)
            return JsonResponse({"error": "User not found"}, status=404)

        # Extract timestamp
        raw_ts = event.get("DeliveredAt") or event.get("ReceivedAt") or event.get("BouncedAt")
        try:
            timestamp_dt = datetime.strptime(raw_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt_timezone.utc) if raw_ts else timezone.now()
        except Exception as e:
            logger.warning("Failed to parse timestamp: %s", raw_ts)
            timestamp_dt = timezone.now()

        logger.debug("📨 Incoming Postmark event: %s", event)

        # Get recipient email (different keys for Delivered/Open vs Bounce)
        recipient_email = event.get("Recipient") or event.get("Email")
        if not recipient_email:
            logger.error("❌ Postmark event missing recipient email: %s", event)
            return JsonResponse({"error": "Missing recipient email"}, status=400)

        # Save SentEmailEvent
        SentEmailEvent.objects.create(
            user=user,
            email=recipient_email,
            event_type=event.get("RecordType"),
            timestamp=timestamp_dt,
            smtp_id=event.get("MessageID", ""),
            user_agent="",  # Not provided by Postmark
            response=event.get("Details", ""),
            custom_args=metadata
        )
        logger.info("✅ Stored Postmark event for user_id: %s", user_id)

        # Update SentEmailRecord if Open event
        if event.get("RecordType") == "Open":
            try:
                record = SentEmailRecord.objects.get(user=user, smtp_id=event.get("MessageID", ""))
                if record.status != "Opened":
                    record.status = "Opened"
                    record.save()
                    logger.info("📬 Updated SentEmailRecord status to Opened for smtp_id: %s", event.get("MessageID"))
            except SentEmailRecord.DoesNotExist:
                logger.warning("No SentEmailRecord found for smtp_id: %s", event.get("MessageID"))

        return JsonResponse({"status": "ok"})

    except Exception as e:
        logger.exception("❌ Failed to process Postmark event")
        return JsonResponse({"error": str(e)}, status=500)

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def about(request):
    return render(request, 'about.html')

def tos(request):
    return render(request, 'tos.html')

def refund_policy(request):
    return render(request, 'refund_policy.html')