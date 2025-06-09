from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.utils import require_google_connection
from .forms import PortfolioForm
from .models import Portfolio, EmailCredit
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.utils.timezone import now
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


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
    portfolio, created = Portfolio.objects.get_or_create(user=request.user)

    is_empty = not (portfolio.major or portfolio.class_year or portfolio.university or portfolio.research_interests or portfolio.resume)
    if created or is_empty:
        request.session['just_created_portfolio'] = True

    editing = request.GET.get('edit') == '1' or request.session.pop('just_created_portfolio', False)

    if request.method == 'POST':
        if 'delete_resume' in request.POST:
            if portfolio.resume:
                portfolio.resume.delete(save=True)
            return redirect('portfolio')

        form = PortfolioForm(request.POST, request.FILES, instance=portfolio)
        if form.is_valid():
            portfolio = form.save()
            return redirect('portfolio')
        else:
            editing = True
    else:
        form = PortfolioForm(instance=portfolio)
        if not editing:
            for field in form.fields.values():
                field.disabled = True

    return render(request, 'portfolio.html', {
        'form': form,
        'portfolio': portfolio,
        'editing': editing,
    })

@login_required
@csrf_exempt
def create_checkout_session(request):
    if request.method == 'POST':
        email_count = int(request.POST.get('email_count', 0))
        portfolio = Portfolio.objects.filter(user=request.user).first()

        if not portfolio or not portfolio.major or not portfolio.university or not portfolio.resume:
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
                pass  # In production, log this issue

    return HttpResponse(status=200)

@login_required
def emails_sent_confirmation(request):
    latest_credit = EmailCredit.objects.filter(user=request.user).order_by('-purchased_at').first()
    return render(request, 'emails_sent.html', {
        'sent_count': latest_credit.count if latest_credit else 0
    })

@login_required
def send_emails_page(request):
    portfolio = Portfolio.objects.filter(user=request.user).first()
    portfolio_complete = bool(
        portfolio and portfolio.major and portfolio.class_year and
        portfolio.university and portfolio.research_interests and portfolio.resume
    )
    return render(request, 'send_emails.html', {
        'portfolio_complete': portfolio_complete,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY
    })
