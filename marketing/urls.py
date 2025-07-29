from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'marketing'

urlpatterns = [
    path('', lambda request: redirect('marketing:loyalty_dashboard'), name='marketing_home'),  # Redirection vers /marketing/loyalty/
    path('loyalty/', views.LoyaltyDashboardView.as_view(), name='loyalty_dashboard'),
]