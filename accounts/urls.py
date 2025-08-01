from django.urls import path, include
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentification allauth
    path('', include('allauth.urls')),
    
    # Pages d'inscription personnalisées
    path('signup/choice/', views.signup_choice, name='signup_choice'),
    path('signup/vendor/', views.vendor_signup, name='vendor_signup'),
    path('signup/buyer/', views.buyer_signup, name='buyer_signup'),
    
    # Profils
    path('profile/', views.profile, name='profile'),
    path('vendor/profile/', views.vendor_profile, name='vendor_profile'),
    path('vendor/<str:username>/', views.vendor_public_profile, name='vendor_public_profile'),
    
    # Actions profil
    path('update-profile-picture/', views.update_profile_picture, name='update_profile_picture'),
    path('delete-account/', views.delete_account, name='delete_account'),
    
    # API vendeur
    path('api/vendor/verification-status/', views.vendor_verification_status, name='vendor_verification_status'),
]