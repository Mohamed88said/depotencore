from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.OverviewView.as_view(), name='overview'),
    path('orders/', views.OrdersView.as_view(), name='orders'),
    path('orders/<int:order_id>/update/', views.OrderUpdateView.as_view(), name='order_update'),
    path('products/', views.ProductsView.as_view(), name='products'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/update/', views.ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    path('requests/', views.RequestsView.as_view(), name='requests'),
    path('requests/<int:request_id>/respond/', views.RespondRequestView.as_view(), name='respond_request'),
    path('reviews/', views.ReviewsView.as_view(), name='reviews'),
    path('reviews/<int:review_id>/reply/', views.ReplyReviewView.as_view(), name='reply_review'),
    path('reviews/<int:review_id>/delete/', views.DeleteReviewView.as_view(), name='delete_review'),
    path('reviews/<int:review_id>/action/', views.ReviewActionView.as_view(), name='review_action'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('reports/', views.ReportsView.as_view(), name='reports'),
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),
    path('return-requests/<int:order_id>/', views.ReturnRequestReviewView.as_view(), name='return_review'),
]