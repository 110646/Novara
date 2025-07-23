from django.contrib import admin
from django.urls import path, include
from core import views as core_views
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.views.generic.base import RedirectView
from core.views import (
    home, dashboard, portfolio, account, contact, postmark_events_webhook,dashboard_stats, log_sent_email, sent_emails_list
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # blocks unwanted allauth routes
    path('accounts/signup/', RedirectView.as_view(url='/', permanent=False)),
    path('accounts/login/', RedirectView.as_view(url='/', permanent=False)),
    path('accounts/logout/', RedirectView.as_view(url='/', permanent=False)),
    path('accounts/password/reset/', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('accounts/password/reset/done/', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('accounts/password/change/', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('accounts/inactive/', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('accounts/confirm-email/', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('accounts/email/', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('accounts/confirm-email/<str:key>/', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('accounts/social/connections/', RedirectView.as_view(pattern_name='home', permanent=False)),
    
    path('accounts/', include('allauth.urls')),

    # custom logout
    path('logout/', core_views.custom_logout, name='logout'),

    # Public
    path('', core_views.home, name='home'),
    path('login/', lambda request: render(request, 'login.html'), name='account_login'),
    path('contact/', core_views.contact, name='contact'),

    # Protected
    path('dashboard/', core_views.dashboard, name='dashboard'),
    path("dashboard/stats/", core_views.dashboard_stats, name="dashboard_stats"),
    path('portfolio/', core_views.portfolio, name='portfolio'),
    path('account/', core_views.account, name='account'),
    path('privacy-policy/', core_views.privacy_policy, name='privacy_policy'),
    path('about/', core_views.about, name='about'),
    path('send-emails/', core_views.send_emails_page, name='send_emails'),
    path('create-checkout-session/', core_views.create_checkout_session, name='create_checkout_session'),
    path('emails-sent/', core_views.emails_sent_confirmation, name='emails_sent_confirmation'),
    path('stripe/webhook/', core_views.stripe_webhook, name='stripe_webhook'),
    path("generate-email-template/", core_views.generate_email_template, name="generate_email_template"),
    path("postmark/events/", core_views.postmark_events_webhook, name="postmark_events_webhook"),
    path('log-sent-email/', core_views.log_sent_email, name='log_sent_email'),
    path('sent-emails/', core_views.sent_emails_list, name='sent_emails_list'),
    path('email-send-status/', core_views.email_send_status, name='email_send_status'),
    path('tos/', core_views.tos, name='tos'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
