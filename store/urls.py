from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # Pages principales
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    
    # Gestion des produits (vendeur)
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/update/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # Panier
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    
    # Checkout et paiement
    path('checkout/', views.checkout, name='checkout'),
    path('payment/process/', views.process_payment, name='process_payment'),
    path('payment/success/<int:order_id>/', views.payment_success, name='payment_success'),
    
    # Adresses
    path('address/add/', views.add_address, name='add_address'),
    
    # Commandes
    path('orders/', views.order_history, name='order_history'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    
    # Favoris
    path('favorites/', views.favorites, name='favorites'),
    path('products/<int:product_id>/toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # Demandes de produits
    path('products/<int:product_id>/request/', views.product_request, name='product_request'),
    
    # Codes promo
    path('apply_promo_code/', views.apply_promo_code, name='apply_promo_code'),
    
    # Signalements
    path('report/', views.ReportCreateView.as_view(), name='report_create'),
    
    # Profils vendeurs
    path('seller/<str:username>/', views.seller_public_profile, name='seller_public_profile'),
    
    # Abonnements
    path('subscription/plans/', views.subscription_plans, name='subscription_plans'),
    path('subscription/create/', views.create_subscription, name='create_subscription'),
    
    # Utilitaires
    path('search/autocomplete/', views.autocomplete_search, name='autocomplete_search'),
]