from django.urls import path, include
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', include('allauth.urls')),
    path('profile/', views.profile, name='profile'),
    path('add_address/', views.add_address, name='add_address'),
    path('seller/<str:username>/', views.seller_profile, name='seller_profile'),
    path('seller-public/<str:username>/', views.seller_public_profile, name='seller_public_profile'),  # Nouvelle route
    path('update-profile-picture/', views.update_profile_picture, name='update_profile_picture'),
    path('delete-account/', views.delete_account, name='delete_account'),
]