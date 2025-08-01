from django.urls import path, include
from . import views

app_name = 'store'

urlpatterns = [
    # === PAGES PUBLIQUES ===
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('category/<slug:slug>/', views.product_list, name='category_products'),
    
    # === API UTILITAIRES ===
    path('api/categories/autocomplete/', views.categories_autocomplete, name='categories_autocomplete'),
]

# URLs vendeur séparées
vendor_patterns = [
    # === GESTION DES PRODUITS ===
    path('products/', views.VendorProductListView.as_view(), name='products'),
    path('products/create/', views.VendorProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/edit/', views.VendorProductUpdateView.as_view(), name='product_edit'),
    path('products/<int:pk>/delete/', views.VendorProductDeleteView.as_view(), name='product_delete'),
    path('products/<int:product_id>/duplicate/', views.product_duplicate, name='product_duplicate'),
    path('products/<int:product_id>/analytics/', views.product_analytics, name='product_analytics'),
    
    # === ACTIONS AJAX ===
    path('products/bulk-action/', views.bulk_product_action, name='bulk_product_action'),
    path('products/<int:product_id>/quick-edit/', views.product_quick_edit, name='product_quick_edit'),
    path('products/<int:product_id>/status/', views.product_status_update, name='product_status_update'),
    
    # === GESTION DES IMAGES ===
    path('products/<int:product_id>/upload-image/', views.upload_product_image, name='upload_product_image'),
    path('products/<int:product_id>/delete-image/', views.delete_product_image, name='delete_product_image'),
    
    # === VARIANTES ===
    path('products/<int:product_id>/variants/', views.product_variants, name='product_variants'),
    path('variants/<int:variant_id>/delete/', views.delete_variant, name='delete_variant'),
    
    # === GESTION DU STOCK ===
    path('stock/', views.stock_management, name='stock_management'),
    path('stock/<int:product_id>/update/', views.update_stock, name='update_stock'),
    
    # === AVIS ===
    path('reviews/', views.vendor_reviews, name='reviews'),
    path('reviews/<int:review_id>/reply/', views.reply_to_review, name='review_reply'),
]

# Inclure les URLs vendeur avec le préfixe 'vendor/'
urlpatterns += [
    path('vendor/', include((vendor_patterns, 'vendor'), namespace='vendor')),
]