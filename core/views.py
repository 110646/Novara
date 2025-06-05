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

@login_required
def portfolio(request):
    portfolio, created = Portfolio.objects.get_or_create(user=request.user)

    # Check if the portfolio is functionally empty
    is_empty = not (portfolio.major or portfolio.class_year or portfolio.university or portfolio.goals or portfolio.resume)

    # If just created or still empty, flag to enter edit mode
    if created or is_empty:
        request.session['just_created_portfolio'] = True

    # Determine if user should be editing
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
def account(request):
    return render(request, 'account.html')

@login_required
def payments(request):
    return render(request, 'payments.html')

@login_required
@require_google_connection
def send_emails(request):
    return render(request, 'emails_sent.html')