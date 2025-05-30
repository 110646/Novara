from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.utils import require_google_connection


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')

@login_required
def dashboard(request):
    google_connected = request.user.socialaccount_set.filter(provider='google').exists()
    return render(request, 'dashboard.html', {'google_connected': google_connected})

@login_required
def portfolio(request):
    return render(request, 'portfolio.html')

@login_required
def account(request):
    return render(request, 'account.html')

@login_required
def payments(request):
    return render(request, 'payments.html')

@login_required
@require_google_connection
def send_emails(request):
    # Email generation and sending logic
    return render(request, 'emails_sent.html')