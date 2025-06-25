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
from .models import EmailCredit, Profile
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.utils.timezone import now
import stripe
import traceback
import json
from openai.types.chat import ChatCompletionMessageParam
from django.contrib.auth import logout
from django.contrib import messages
from storages.backends.s3boto3 import S3Boto3Storage
from core.choices import MAJOR_CHOICES, CLASS_YEAR_CHOICES, US_UNIVERSITY_CHOICES
from django.core.mail import send_mail

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
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('home')

# ------------------------------
# DASHBOARD + PAGES
# ------------------------------
@login_required
def dashboard(request):
    google_connected = request.user.socialaccount_set.filter(provider='google').exists()
    return render(request, 'dashboard.html', {'google_connected': google_connected})

@login_required
def account(request):
    return render(request, 'account.html')

@login_required
def payments(request):
    credits = EmailCredit.objects.filter(user=request.user).order_by('-purchased_at')
    total = sum(c.count for c in credits)
    return render(request, 'payments.html', {
        'credits': credits,
        'total_credits': total
    })

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
        print("❌ Error fetching Supabase portfolio:", e)

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
                print("❌ Resume deletion error:", e)

        elif resume_file:
            try:
                s3_storage = S3Boto3Storage()
                path = s3_storage.save(f'resumes/{resume_file.name}', resume_file)
                resume_url = s3_storage.url(path)
                print(f"✅ Resume uploaded to R2: {resume_url}")
            except Exception as e:
                print("❌ Resume upload error:", e)

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
        name = request.POST.get("name")
        email = request.POST.get("email")
        major = request.POST.get("major")
        university = request.POST.get("university")
        research_interests = request.POST.get("research_interests")
        class_year = request.POST.get("class_year")
        resume_file = request.FILES.get("resume")

        if not resume_file:
            return JsonResponse({"error": "Resume file missing"}, status=400)

        prompt = f"""
You are an academic writing assistant. Write a professional cold outreach email on behalf of a student named {name}, who is majoring in {major} at {university} and expects to graduate in {class_year}. The email is being sent to a professor.

The student's resume is attached. Their stated research interests are: {research_interests}.

Your job is to generate a polished, respectful, and enthusiastic email that:

- Clearly expresses interest in joining the professor's research group
- Highlights relevant accomplishments and skills from the resume
- Ties their research interests and long-term goals to the professor's and student's major
- Ends with a polite, actionable closing (e.g., asking about opportunities)

Format requirements:
- Use **only** these placeholders: {{ professor_name }}, {{ university }}
- Do **not** invent any fields like [specific area of research] or [insert XYZ]
- Do **not** use markdown, bold, or special formatting — plain text only
- Keep the email **3 to 5 concise paragraphs**
- End the email with:
{name}
{email}
(include phone number only if found in the resume)

Do not include any preamble or commentary. Only return the finalized email body.
""".strip()

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # ✅ Properly format the file as a tuple
        uploaded_file = client.files.create(
            file=("resume.pdf", resume_file.read(), "application/pdf"),
            purpose="assistants"
        )

        # ✅ Now call the chat completion with the file context
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an academic writing assistant."},
                {"role": "user", "content": prompt}
            ],
            file_ids=[uploaded_file.id]
        )

        template = response.choices[0].message.content.strip()
        return JsonResponse({"template": template})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


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
                send_emails_after_payment(user.id)
            except User.DoesNotExist:
                return HttpResponse(status=404)

    return HttpResponse(status=200)

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

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        # Send email
        subject = f"Contact Form: {name}"
        email_message = f"""
From: {name} ({email})

Message:
{message}
        """
        to_email = 'helpnovaraco@gmail.com'
        
        try:
            # Send the email
            send_mail(
                subject,
                email_message,
                'noreply@novara.com',  # From email
                [to_email],
                fail_silently=False,
            )
            print(f"✅ Email sent successfully to {to_email}")
            messages.success(request, 'Thank you for your message! We will get back to you soon.')
        except Exception as e:
            print(f"❌ Email sending error: {str(e)}")
            messages.error(request, f'Sorry, there was an error sending your message: {str(e)}')
        
        return redirect('contact')
    
    return render(request, 'contact.html')