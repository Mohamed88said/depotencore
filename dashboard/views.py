from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, View
from django.db.models import Sum, Count, Avg
from store.models import Order, OrderItem, Product, ProductView, Notification, ProductRequest, Review, SellerProfile
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from datetime import datetime
from django.urls import reverse
from django.db.models.functions import TruncDate, TruncMonth
from .forms import StatisticsFilterForm, ProductForm, ReturnRequestForm
from prophet import Prophet
import pandas as pd
from decimal import Decimal
from admin_panel.models import ProductModeration
from datetime import timedelta
from returns.models import ReturnRequest
import csv

class OverviewView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.user_type not in ['seller', 'admin']:
            raise PermissionDenied("Accès réservé aux vendeurs et admins")
        
        context['total_revenue'] = OrderItem.objects.filter(
            product__seller=user, order__status__in=['shipped', 'delivered']
        ).aggregate(total=Sum('price'))['total'] or 0
        context['total_orders'] = Order.objects.filter(items__product__seller=user).distinct().count()
        context['total_products'] = Product.objects.filter(seller=user).count()
        context['notifications'] = Notification.objects.filter(user=user).order_by('-created_at')[:5]
        return context

class OrdersView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/orders.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.user_type not in ['seller', 'admin']:
            raise PermissionDenied("Accès réservé aux vendeurs et admins")
        
        context['orders'] = Order.objects.filter(items__product__seller=user).distinct().order_by('-created_at')
        return context

class OrderUpdateView(LoginRequiredMixin, View):
    def post(self, request, order_id):
        if request.user.user_type not in ['seller', 'admin']:
            raise PermissionDenied("Accès réservé aux vendeurs et admins")
        
        order = get_object_or_404(
            Order.objects.filter(
                id=order_id,
                items__product__seller=request.user
            ).distinct()
        )
        
        new_status = request.POST.get('status')
        response_data = {'success': False, 'message': 'Statut invalide.'}
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            response_data['success'] = True
            response_data['message'] = f"Statut de la commande #{order_id} mis à jour avec succès en {order.get_status_display()}."
        return JsonResponse(response_data)

    def get(self, request, order_id):
        return JsonResponse({'error': 'Cette action nécessite une requête POST'}, status=405)

class ReturnRequestReviewView(LoginRequiredMixin, View):
    template_name = 'dashboard/return_review.html'

    def get(self, request, order_id):
        if request.user.user_type not in ['seller', 'admin']:
            raise PermissionDenied("Accès réservé aux vendeurs et admins")
        
        order = get_object_or_404(
            Order.objects.filter(
                id=order_id,
                items__product__seller=request.user
            ).distinct()
        )
        return_requests = ReturnRequest.objects.filter(order=order)
        if not return_requests.exists():
            messages.error(request, f"Aucune demande de retour trouvée pour la commande {order_id}.")
            return redirect('dashboard:orders')
        return render(request, self.template_name, {'return_request': return_requests.latest('created_at')})

    def post(self, request, order_id):
        if request.user.user_type not in ['seller', 'admin']:
            raise PermissionDenied("Accès réservé aux vendeurs et admins")
        
        order = get_object_or_404(
            Order.objects.filter(
                id=order_id,
                items__product__seller=request.user
            ).distinct()
        )
        return_requests = ReturnRequest.objects.filter(order=order)
        if not return_requests.exists():
            messages.error(request, f"Aucune demande de retour trouvée pour la commande {order_id}.")
            return redirect('dashboard:orders')
        
        return_request = return_requests.latest('created_at')
        action = request.POST.get('action')
        if action == 'approve':
            return_request.status = 'APPROVED'
            messages.success(request, f"Demande de retour #{return_request.id} approuvée.")
        elif action == 'reject':
            return_request.status = 'REJECTED'
            messages.success(request, f"Demande de retour #{return_request.id} rejetée.")
        return_request.save()
        return redirect('dashboard:orders')

class ProductsView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'dashboard/product_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        user = self.request.user
        if user.user_type not in ['seller', 'admin']:
            raise PermissionDenied("Accès réservé aux vendeurs et admins")
        return Product.objects.filter(seller=user, is_sold=False, sold_out=False).order_by('-created_at')

class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'dashboard/product_form.html'

    def form_valid(self, form):
        product = form.save(commit=False)
        product.seller = self.request.user
        product.save()
        ProductModeration.objects.create(
            product=product,
            moderator=None,
            status='pending',
            reason='Nouveau produit en attente d\'approbation'
        )
        messages.success(self.request, 'Produit soumis pour approbation.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('dashboard:products')

class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'dashboard/product_form.html'

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)

    def get_success_url(self):
        return reverse('dashboard:products')

class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'dashboard/product_confirm_delete.html'
    success_url = '/dashboard/products/'

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)

class RequestsView(LoginRequiredMixin, ListView):
    model = ProductRequest
    template_name = 'dashboard/requests.html'
    context_object_name = 'requests'

    def get_queryset(self):
        user = self.request.user
        if user.user_type not in ['seller', 'admin']:
            raise PermissionDenied("Accès réservé aux vendeurs et admins")
        return ProductRequest.objects.filter(product__seller=user).order_by('-created_at')

class RespondRequestView(LoginRequiredMixin, View):
    def post(self, request, request_id):
        request_obj = get_object_or_404(ProductRequest, id=request_id, product__seller=request.user)
        response = request.POST.get('response')
        request_obj.response = response
        request_obj.save()
        messages.success(request, f"Demande {request_id} répondue avec succès.")
        return redirect('dashboard:requests')

class ReviewsView(LoginRequiredMixin, ListView):
    model = Review
    template_name = 'dashboard/reviews.html'
    context_object_name = 'reviews'

    def get_queryset(self):
        user = self.request.user
        if user.user_type not in ['seller', 'admin']:
            raise PermissionDenied("Accès réservé aux vendeurs et admins")
        return Review.objects.filter(product__seller=user).order_by('-created_at')

class ReplyReviewView(LoginRequiredMixin, View):
    def post(self, request, review_id):
        review = get_object_or_404(Review, id=review_id, product__seller=request.user)
        reply = request.POST.get('reply')
        review.reply = reply
        review.save()
        messages.success(request, f"Réponse ajoutée à l'avis {review_id}.")
        return redirect('dashboard:reviews')

class DeleteReviewView(LoginRequiredMixin, DeleteView):
    model = Review
    template_name = 'dashboard/review_confirm_delete.html'
    success_url = '/dashboard/reviews/'

    def get_queryset(self):
        return Review.objects.filter(product__seller=self.request.user)

class ProfileView(LoginRequiredMixin, UpdateView):
    model = SellerProfile
    fields = ['first_name', 'last_name', 'description', 'business_name', 'business_address', 'contact_phone', 'profile_picture']
    template_name = 'dashboard/profile.html'

    def get_object(self):
        return self.request.user.seller_profile

    def get_success_url(self):
        return reverse('dashboard:profile')

class ReportsView(LoginRequiredMixin, View):
    def get(self, request):
        if request.user.user_type not in ['seller', 'admin']:
            raise PermissionDenied("Accès réservé aux vendeurs et admins")
        
        orders = Order.objects.filter(items__product__seller=request.user, status='delivered')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_report_' + datetime.now().strftime('%Y%m%d') + '.csv"'
        writer = csv.writer(response)
        writer.writerow(['Order ID', 'Date', 'Total', 'Customer'])
        for order in orders:
            writer.writerow([order.id, order.created_at, order.total, order.user.username])
        return response

class StatisticsView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/statistics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.user_type not in ['seller', 'admin']:
            raise PermissionDenied("Accès réservé aux vendeurs et admins")

        # Formulaire de filtre avec horizon personnalisé
        form = StatisticsFilterForm(self.request.GET or None)
        horizon = self.request.GET.get('horizon', '3')
        try:
            horizon = int(horizon)
        except (ValueError, TypeError):
            horizon = 3
        context['filter_form'] = form
        context['horizon'] = str(horizon)

        # Base QuerySets
        base_qs = OrderItem.objects.filter(product__seller=user)
        product_qs = Product.objects.filter(seller=user)
        request_qs = ProductRequest.objects.filter(product__seller=user)
        view_qs = ProductView.objects.filter(product__seller=user)
        review_qs = Review.objects.filter(product__seller=user)

        # Appliquer les filtres
        if form.is_valid():
            if form.cleaned_data['start_date']:
                start_date = form.cleaned_data['start_date']
                base_qs = base_qs.filter(order__created_at__gte=start_date)
                product_qs = product_qs.filter(created_at__gte=start_date)
                request_qs = request_qs.filter(created_at__gte=start_date)
                view_qs = view_qs.filter(view_date__gte=start_date)
                review_qs = review_qs.filter(created_at__gte=start_date)
            if form.cleaned_data['end_date']:
                end_date = form.cleaned_data['end_date']
                base_qs = base_qs.filter(order__created_at__lte=end_date)
                product_qs = product_qs.filter(created_at__lte=end_date)
                request_qs = request_qs.filter(created_at__lte=end_date)
                view_qs = view_qs.filter(view_date__lte=end_date)
                review_qs = review_qs.filter(created_at__lte=end_date)
            if form.cleaned_data['category']:
                category = form.cleaned_data['category']
                product_qs = product_qs.filter(category=category)
                base_qs = base_qs.filter(product__category=category)
                request_qs = request_qs.filter(product__category=category)
                view_qs = view_qs.filter(product__category=category)
                review_qs = review_qs.filter(product__category=category)

        # Ventes par mois
        sales_data = base_qs.annotate(month=TruncMonth('order__created_at')).values('month').annotate(total=Sum('price')).order_by('month')
        context['sales_labels'] = [item['month'].strftime('%Y-%m') if item['month'] else 'N/A' for item in sales_data]
        context['sales_data'] = [float(item['total'] or 0) for item in sales_data]
        context['total_sales'] = sum(context['sales_data']) if context['sales_data'] else 0
        context['avg_monthly_sales'] = context['total_sales'] / len(context['sales_data']) if context['sales_data'] else 0

        # Prévisions avec Prophet
        context['forecast_labels'] = []
        context['forecast_data'] = []
        if context['sales_labels'] and len(context['sales_labels']) >= 2:  # Minimum 2 points pour Prophet
            try:
                df = pd.DataFrame({
                    'ds': [pd.to_datetime(label) for label in context['sales_labels']],
                    'y': context['sales_data']
                })
                model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
                model.fit(df)
                future = model.make_future_dataframe(periods=horizon, freq='M')
                forecast = model.predict(future)
                future_dates = forecast['ds'].tail(horizon).tolist()
                context['forecast_labels'] = [d.strftime('%Y-%m') for d in future_dates]
                context['forecast_data'] = [max(0, float(y)) for y in forecast['yhat'].tail(horizon)]
            except Exception as e:
                context['forecast_labels'] = []
                context['forecast_data'] = []
        if not context['forecast_labels']:
            context['forecast_labels'] = []
            context['forecast_data'] = []

        # Intégration des statuts des commandes
        pending_orders = Order.objects.filter(items__product__seller=user, status='pending').aggregate(total=Sum('items__price'))['total'] or Decimal('0')
        processing_orders = Order.objects.filter(items__product__seller=user, status='processing').aggregate(total=Sum('items__price'))['total'] or Decimal('0')
        shipped_orders = Order.objects.filter(items__product__seller=user, status='shipped').aggregate(total=Sum('items__price'))['total'] or Decimal('0')
        delivered_orders = Order.objects.filter(items__product__seller=user, status='delivered').aggregate(total=Sum('items__price'))['total'] or Decimal('0')
        context['short_term_forecast'] = float(pending_orders * Decimal('0.5') + processing_orders * Decimal('0.7'))
        context['order_status_breakdown'] = {
            'pending': float(pending_orders),
            'processing': float(processing_orders),
            'shipped': float(shipped_orders),
            'delivered': float(delivered_orders)
        }

        # Vues des produits
        views_data = view_qs.values('view_date').annotate(total_views=Sum('view_count')).order_by('view_date')
        context['view_labels'] = [
            item['view_date'].strftime('%Y-%m-%d') if item['view_date'] and hasattr(item['view_date'], 'strftime') else 'N/A'
            for item in views_data
        ]
        context['view_data'] = [int(item['total_views'] or 0) for item in views_data]
        recent_views = sum(context['view_data'][-7:]) if context['view_data'] and len(context['view_data']) >= 7 else sum(context['view_data'] or [0])
        context['view_influence'] = float(recent_views * Decimal('0.1'))
        context['total_views'] = sum(context['view_data']) if context['view_data'] else 0

        # Taux de conversion (ventes / vues)
        total_sold = base_qs.aggregate(total_sold=Sum('quantity'))['total_sold'] or 0
        context['conversion_rate'] = (total_sold / context['total_views'] * 100) if context['total_views'] > 0 else None

        # Stocks par produit
        stock_data = product_qs.values('name').annotate(total_stock=Sum('stock')).order_by('name')
        context['stock_labels'] = [item['name'] or 'N/A' for item in stock_data]
        context['stock_data'] = [int(item['total_stock'] or 0) for item in stock_data]
        context['total_stock'] = sum(context['stock_data']) if context['stock_data'] else 0
        context['min_stock'] = min(context['stock_data']) if context['stock_data'] else float('inf')
        context['avg_stock_per_product'] = context['total_stock'] / len(context['stock_data']) if context['stock_data'] else 0

        # Stocks critiques
        low_stock_threshold = 10
        low_stock_products = product_qs.filter(stock__lt=low_stock_threshold).values('name', 'stock')
        context['low_stock_products'] = list(low_stock_products)
        revenue_impact = OrderItem.objects.filter(
            product__seller=user,
            product__name__in=[p['name'] for p in low_stock_products],
            order__status__in=['shipped', 'delivered']
        ).aggregate(total=Sum('price'))['total'] or 0
        context['low_stock_revenue_impact'] = float(revenue_impact)

        # Commandes par jour
        orders_data = Order.objects.filter(items__product__seller=user).annotate(day=TruncDate('created_at')).values('day').annotate(count=Count('id')).order_by('day')
        context['orders_labels'] = [item['day'].strftime('%Y-%m-%d') if item['day'] else 'N/A' for item in orders_data]
        context['orders_data'] = [int(item['count'] or 0) for item in orders_data]
        context['total_orders_count'] = sum(context['orders_data']) if context['orders_data'] else 0
        context['avg_daily_orders'] = context['total_orders_count'] / len(context['orders_labels']) if context['orders_labels'] else 0

        # Produits les mieux vendus
        top_products = base_qs.values('product__name').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:5]
        context['top_products_labels'] = [item['product__name'] or 'N/A' for item in top_products]
        context['top_products_data'] = [int(item['total_sold'] or 0) for item in top_products]
        context['top_product_revenue'] = base_qs.filter(product__name__in=context['top_products_labels']).aggregate(total=Sum('price'))['total'] or 0

        # Demandes par produit
        requests_data = request_qs.values('product__name').annotate(count=Count('id')).order_by('-count')[:5]
        context['requests_labels'] = [item['product__name'] or 'N/A' for item in requests_data]
        context['requests_data'] = [int(item['count'] or 0) for item in requests_data]
        context['total_requests'] = sum(context['requests_data']) if context['requests_data'] else 0

        # Avis par produit
        reviews_data = review_qs.values('product__name').annotate(avg_rating=Avg('rating'), review_count=Count('id')).order_by('-avg_rating')[:5]
        context['reviews_labels'] = [item['product__name'] or 'N/A' for item in reviews_data]
        context['reviews_avg_data'] = [float(item['avg_rating'] or 0) for item in reviews_data]
        context['reviews_count_data'] = [int(item['review_count'] or 0) for item in reviews_data]
        context['min_reviews_avg'] = min(context['reviews_avg_data']) if context['reviews_avg_data'] else float('inf')
        context['total_reviews'] = review_qs.count()

        # Combinaison Ventes vs Stocks
        sales_vs_stock = base_qs.values('product__name').annotate(
            total_sold=Sum('quantity'), 
            remaining_stock=Sum('product__stock')
        ).order_by('-total_sold')[:5]
        context['sales_vs_stock_labels'] = [item['product__name'] or 'N/A' for item in sales_vs_stock]
        context['sales_vs_stock_sold'] = [int(item['total_sold'] or 0) for item in sales_vs_stock]
        context['sales_vs_stock_remaining'] = [int(item['remaining_stock'] or 0) for item in sales_vs_stock]
        context['min_sales_vs_stock_remaining'] = min(context['sales_vs_stock_remaining']) if context['sales_vs_stock_remaining'] else float('inf')

        # Activité globale
        activity_data = {
            'orders': context['total_orders_count'],
            'revenue': base_qs.aggregate(total=Sum('price'))['total'] or 0,
            'requests': context['total_requests'],
            'stocks': context['total_stock'],
        }
        context['activity_labels'] = ['Commandes', 'Revenus (€)', 'Demandes', 'Stocks']
        context['activity_data'] = [
            float(activity_data['orders']), 
            float(activity_data['revenue'] or 0), 
            float(activity_data['requests'] or 0), 
            float(activity_data['stocks'])
        ]

        # Résumé détaillé
        conversion_rate_display = f"{context['conversion_rate']:.2f}" if context['conversion_rate'] is not None else 'N/A'
        summary = f"""
        <h3>Résumé de votre tableau de bord - {datetime.now().strftime('%d/%m/%Y %H:%M')} (CEST)</h3>
        <h4>Ventes</h4>
        <ul>
            <li>Ventes totales : {context['total_sales']:.2f} €</li>
            <li>Ventes par mois : {', '.join(context['sales_labels'])} - {', '.join([f'{x:.2f}' for x in context['sales_data']])} €</li>
            <li>Moyenne mensuelle : {context['avg_monthly_sales']:.2f} € - Comparez avec les prévisions pour ajuster.</li>
            <li>Prévisions ({horizon} mois) : {sum(context['forecast_data']):.2f} € - Basé sur les tendances historiques.</li>
            <li><strong>Conseil</strong> : Si les ventes baissent, envisagez des ajustements de prix ou des publicités ciblées.</li>
        </ul>
        <h4>Statut des Commandes</h4>
        <ul>
            <li>En attente : {context['order_status_breakdown']['pending']:.2f} €</li>
            <li>En traitement : {context['order_status_breakdown']['processing']:.2f} €</li>
            <li>Expédiées : {context['order_status_breakdown']['shipped']:.2f} €</li>
            <li>Livrées : {context['order_status_breakdown']['delivered']:.2f} €</li>
            <li><strong>Recommandation</strong> : Accélérez le traitement des commandes en attente.</li>
        </ul>
        <h4>Vues des Produits</h4>
        <ul>
            <li>Vues totales : {context['total_views']} ({', '.join(context['view_labels'])})</li>
            <li>Impact estimé : {context['view_influence']:.2f} € - Basé sur les 7 derniers jours.</li>
            <li>Taux de conversion : {conversion_rate_display} % - Ventes par rapport aux vues.</li>
            <li><strong>Recommandation</strong> : Si le taux est faible, améliorez les descriptions et images.</li>
        </ul>
        <h4>Stocks</h4>
        <ul>
            <li>Stocks totaux : {context['total_stock']} unités ({', '.join([f'{label}: {stock}' for label, stock in zip(context['stock_labels'], context['stock_data'])])})</li>
            <li>Moyenne par produit : {context['avg_stock_per_product']:.2f} unités - Évaluez l’uniformité.</li>
            <li>Stocks critiques : {len(context['low_stock_products'])} produits < {low_stock_threshold} unités, impact sur revenus : {context['low_stock_revenue_impact']:.2f} €</li>
            <li><strong>Conseil</strong> : Reconstituez les stocks critiques pour éviter les pertes de ventes.</li>
        </ul>
        <h4>Commandes</h4>
        <ul>
            <li>Commandes totales : {context['total_orders_count']} ({', '.join(context['orders_labels'])} - {', '.join(map(str, context['orders_data']))})</li>
            <li>Moyenne quotidienne : {context['avg_daily_orders']:.2f} commandes - Suivez les tendances.</li>
            <li>Prévision à court terme : {context['short_term_forecast']:.2f} € - Basée sur les statuts.</li>
            <li><strong>Recommandation</strong> : Analysez les pics pour planifier les stocks.</li>
        </ul>
        <h4>Produits les Mieux Vendus</h4>
        <ul>
            <li>Top 5 : {', '.join([f'{label}: {data}' for label, data in zip(context['top_products_labels'], context['top_products_data'])])} unités</li>
            <li>Revenus des best-sellers : {context['top_product_revenue']:.2f} € - Contribution majeure.</li>
            <li><strong>Conseil</strong> : Mettez en avant ces produits via des ajustements de prix ou publicités.</li>
        </ul>
        <h4>Demandes</h4>
        <ul>
            <li>Demandes totales : {context['total_requests']} ({', '.join([f'{label}: {data}' for label, data in zip(context['requests_labels'], context['requests_data'])])})</li>
            <li><strong>Recommandation</strong> : Répondez rapidement pour convertir en ventes.</li>
        </ul>
        <h4>Avis</h4>
        <ul>
            <li>Avis totaux : {context['total_reviews']} produits</li>
            <li>Top 5 : {', '.join([f'{label}: {avg:.1f} ({count})' for label, avg, count in zip(context['reviews_labels'], context['reviews_avg_data'], context['reviews_count_data'])])} - Min : {context['min_reviews_avg']:.1f}</li>
            <li><strong>Conseil</strong> : Répondez aux avis faibles pour améliorer la satisfaction.</li>
        </ul>
        <h4>Ventes vs Stocks</h4>
        <ul>
            <li>Comparaison : {', '.join([f'{label}: {sold} vendus, {remaining} restants' for label, sold, remaining in zip(context['sales_vs_stock_labels'], context['sales_vs_stock_sold'], context['sales_vs_stock_remaining'])])} - Min restant : {context['min_sales_vs_stock_remaining']}</li>
            <li><strong>Recommandation</strong> : Équilibrez les stocks pour répondre à la demande.</li>
        </ul>
        <h4>Activité Globale</h4>
        <ul>
            <li>Résumé : {context['activity_data'][0]} commandes, {context['activity_data'][1]:.2f} €, {context['activity_data'][2]} demandes, {context['activity_data'][3]} stocks</li>
            <li><strong>Conseil</strong> : Si croissance, investissez dans la publicité ou l’expansion.</li>
        </ul>
        """
        context['summary'] = summary

        # Données pour les graphiques (harmonisation)
        context['chart_sales'] = {
            'labels': context['sales_labels'],
            'data': context['sales_data'],
            'title': 'Ventes par Mois (€)'
        }
        context['chart_orders'] = {
            'labels': context['orders_labels'],
            'data': context['orders_data'],
            'title': 'Commandes par Jour'
        }
        context['chart_stock'] = {
            'labels': context['stock_labels'],
            'data': context['stock_data'],
            'title': 'Stocks par Produit'
        }
        context['chart_top_products'] = {
            'labels': context['top_products_labels'],
            'data': context['top_products_data'],
            'title': 'Produits les Mieux Vendus'
        }
        context['chart_requests'] = {
            'labels': context['requests_labels'],
            'data': context['requests_data'],
            'title': 'Demandes par Produit'
        }
        context['chart_reviews'] = {
            'labels': context['reviews_labels'],
            'avg_data': context['reviews_avg_data'],
            'count_data': context['reviews_count_data'],
            'title': 'Avis par Produit'
        }
        context['chart_sales_vs_stock'] = {
            'labels': context['sales_vs_stock_labels'],
            'sold_data': context['sales_vs_stock_sold'],
            'remaining_data': context['sales_vs_stock_remaining'],
            'title': 'Ventes vs Stocks'
        }
        context['chart_activity'] = {
            'labels': context['activity_labels'],
            'data': context['activity_data'],
            'title': 'Activité Globale'
        }
        context['chart_forecast'] = {
            'labels': context['forecast_labels'],
            'data': context['forecast_data'],
            'title': f'Prévisions des Ventes ({horizon} mois)'
        }
        context['chart_order_status'] = {
            'labels': list(context['order_status_breakdown'].keys()),
            'data': list(context['order_status_breakdown'].values()),
            'title': 'Statut des Commandes (€)'
        }

        return context

class ReviewActionView(LoginRequiredMixin, View):
    def post(self, request, review_id):
        review = get_object_or_404(Review, id=review_id, product__seller=request.user)
        action = request.POST.get('action')
        if action == 'approve':
            review.is_approved = True
            messages.success(request, f"L'avis #{review_id} a été approuvé.")
        elif action == 'reject':
            review.is_approved = False
            messages.success(request, f"L'avis #{review_id} a été rejeté.")
        review.save()
        return redirect('dashboard:reviews')

class BuyerOrdersView(LoginRequiredMixin, ListView):
    template_name = 'dashboard/orders.html'
    context_object_name = 'orders'

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['seller', 'admin']:
            raise PermissionDenied("Accès réservé aux acheteurs")
        return Order.objects.filter(user=user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['return_form'] = ReturnRequestForm()
        return context

class ReturnRequestCreateView(LoginRequiredMixin, View):
    def post(self, request, order_id):
        user = request.user
        if user.user_type in ['seller', 'admin']:
            raise PermissionDenied("Accès réservé aux acheteurs")
        order = get_object_or_404(Order, id=order_id, user=user)
        form = ReturnRequestForm(request.POST, request.FILES)
        if form.is_valid():
            return_request = form.save(commit=False)
            return_request.order = order
            return_request.user = user
            return_request.save()
            messages.success(request, f"Demande de retour pour la commande #{order_id} soumise avec succès.")
            return redirect('dashboard:orders')
        messages.error(request, "Erreur dans le formulaire de retour.")
        return redirect('dashboard:orders')