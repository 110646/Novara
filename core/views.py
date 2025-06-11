from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.utils import require_google_connection
import httpx
import os
from django.core.files.storage import default_storage
from .models import EmailCredit
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.utils.timezone import now
import stripe
import traceback
from storages.backends.s3boto3 import S3Boto3Storage
from core.choices import MAJOR_CHOICES, CLASS_YEAR_CHOICES, US_UNIVERSITY_CHOICES

stripe.api_key = settings.STRIPE_SECRET_KEY
SUPABASE_URL = "https://qdlguxijkkuujnaeuhqq.supabase.co"
SUPABASE_API_KEY = settings.SUPABASE_SERVICE_ROLE_KEY


# ------------------------------
# PUBLIC
# ------------------------------
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


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

    if request.method == 'POST':
        name = request.POST.get('name')
        major = request.POST.get('major')
        class_year = request.POST.get('class_year')
        university = request.POST.get('university')
        research_interests = request.POST.get('research_interests')
        resume_file = request.FILES.get('resume')
        resume_url = portfolio_data.get("resume_url")

        if "delete_resume" in request.POST:
            resume_url = None  # Set to None to clear
            try:
                if portfolio_data.get("resume_url"):
                    from boto3 import client
                    s3 = client("s3")
                    key = portfolio_data["resume_url"].split("/")[-2] + "/" + portfolio_data["resume_url"].split("/")[-1]
                    s3.delete_object(Bucket="your-bucket-name", Key=key)
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
            "email": user.email,
            "major": major,
            "class_year": class_year,
            "university": university,
            "research_interests": research_interests,
            "resume_url": resume_url,
            "updated_at": now().isoformat()
        }

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

    resume_filename = os.path.basename(portfolio_data.get("resume_url", "")) if portfolio_data.get("resume_url") else ""
    return render(request, 'portfolio.html', {
        'portfolio': portfolio_data,
        'editing': editing,
        'resume_filename': resume_filename,
        'major_choices': MAJOR_CHOICES,
        'class_year_choices': CLASS_YEAR_CHOICES,
        'university_choices': US_UNIVERSITY_CHOICES,
    })

@login_required
@csrf_exempt
def create_checkout_session(request):
    if request.method == 'POST':
        email_count = int(request.POST.get('email_count', 0))

        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}"
        }
        params = {"user_id": f"eq.{request.user.id}"}
        response = httpx.get(f"{SUPABASE_URL}/rest/v1/portfolios", headers=headers, params=params)

        portfolio = response.json()[0] if response.status_code == 200 and response.json() else {}

        if not portfolio or not portfolio.get("major") or not portfolio.get("university") or not portfolio.get("resume_url"):
            return JsonResponse({'error': 'Portfolio incomplete'}, status=400)

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
            except User.DoesNotExist:
                pass  

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