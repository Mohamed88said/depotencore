from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    path('order/<int:order_id>/submit-location/', views.submit_location, name='submit_location'),
    path('order/<int:order_id>/suggest-location/', views.suggest_location, name='suggest_location'),
    path('delivery/<int:delivery_id>/assign/', views.assign_delivery, name='assign_delivery'),
    path('order/<int:order_id>/submit-location/', views.submit_location, name='submit_location'),
    # Autres routes...
]