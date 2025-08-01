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
    
    # Géolocalisation
    path('geocode/', views.geocode, name='geocode'),
    
    # Vendeur - commandes
    path('seller/orders/', views.seller_order_list, name='seller_order_list'),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    
    # Marquer comme vendu
    path('products/<int:product_id>/mark-sold/', views.mark_as_sold, name='mark_as_sold'),
    
    # Réductions
    path('products/<int:product_id>/apply-discount/', views.apply_discount_for_product, name='apply_discount_for_product'),
    path('apply-discount-multiple/', views.apply_discount_multiple, name='apply_discount_multiple'),
    
    # Messages/Chat
    path('messages/', views.messages_view, name='messages'),
    path('message-seller/<int:product_id>/', views.message_seller, name='message_seller'),
    
    # Avis
    path('reviews/<int:review_id>/reply/', views.reply_to_review, name='reply_to_review'),
    
    # Répondre aux demandes de produits
    path('requests/<int:request_id>/respond/', views.respond_product_request, name='respond_product_request'),
    
    # Noter un vendeur
    path('orders/<int:order_id>/rate-seller/', views.rate_seller, name='rate_seller'),
    
    # Profil vendeur (modification)
    path('seller-profile/', views.seller_profile, name='seller_profile'),
    
    # === URLs QR Code et livraison ===
    path('delivery/scan/<str:code>/', views.scan_qr_payment, name='scan_qr_payment'),
    path('delivery/scan/<str:code>/process/', views.process_qr_payment, name='process_qr_payment'),
    path('delivery/scan/<str:code>/confirm/', views.delivery_confirmation, name='delivery_confirmation'),
    path('delivery/qr/<int:order_id>/', views.view_qr_code, name='view_qr_code'),
    path('payment/verify/<int:order_id>/', views.payment_verification, name='payment_verification'),
    path('payment/stripe/confirm/', views.confirm_stripe_payment, name='confirm_stripe_payment'),
    path('vendor/orders/pending/', views.vendor_pending_orders, name='vendor_pending_orders'),
    
    # === URLs interface vendeur livraison ===
    path('vendor/delivery/choice/<int:order_id>/', views.assign_delivery_choice, name='assign_delivery_choice'),
    path('vendor/delivery/select/<int:order_id>/', views.select_delivery_person, name='select_delivery_person'),
    path('vendor/delivery/marketplace/<int:order_id>/', views.publish_to_marketplace, name='publish_to_marketplace'),
    path('vendor/delivery/cancel/<int:order_id>/', views.cancel_delivery_assignment, name='cancel_delivery_assignment'),
    
    # === URLs marketplace livreur ===
    path('delivery/marketplace/', views.delivery_marketplace, name='delivery_marketplace'),
    path('delivery/accept/<int:assignment_id>/', views.accept_delivery_assignment, name='accept_delivery_assignment'),
    path('delivery/reject/<int:assignment_id>/', views.reject_delivery_assignment, name='reject_delivery_assignment'),
    path('delivery/pickup/<int:assignment_id>/', views.mark_picked_up, name='mark_picked_up'),
    path('delivery/complete/<int:assignment_id>/', views.complete_delivery_assignment, name='complete_delivery_assignment'),
    path('delivery/profile/', views.delivery_profile_management, name='delivery_profile_management'),
    
    # === URLs pour les livreurs ===
    path('delivery/dashboard/', views.delivery_dashboard, name='delivery_dashboard'),
    path('delivery/orders/', views.delivery_orders, name='delivery_orders'),
    path('delivery/accept/<int:order_id>/', views.accept_delivery, name='accept_delivery'),
    path('delivery/start/<int:order_id>/', views.start_delivery, name='start_delivery'),
    path('delivery/complete/<int:order_id>/', views.complete_delivery, name='complete_delivery'),
    path('delivery/update-location/', views.update_delivery_location, name='update_delivery_location'),
    path('delivery/profile/', views.delivery_profile, name='delivery_profile'),
]