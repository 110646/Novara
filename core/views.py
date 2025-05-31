from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.utils import require_google_connection
from .forms import PortfolioForm
from .models import Portfolio


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')

@login_required
def dashboard(request):
    google_connected = request.user.socialaccount_set.filter(provider='google').exists()
    return render(request, 'dashboard.html', {'google_connected': google_connected})

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import PortfolioForm
from .models import Portfolio

@login_required
def portfolio(request):
    portfolio, created = Portfolio.objects.get_or_create(user=request.user)
    editing = request.GET.get('edit', created) 

    if request.method == 'POST':
        form = PortfolioForm(request.POST, request.FILES, instance=portfolio)
        if form.is_valid():
            form.save()
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
def account(request):
    return render(request, 'account.html')

@login_required
def payments(request):
    return render(request, 'payments.html')

@login_required
@require_google_connection
def send_emails(request):
    return render(request, 'emails_sent.html')