# store/views.py - Vues pour la gestion des produits vendeur

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from decimal import Decimal
import json

from .models import (
    Product, Category, ProductVariant, ProductModeration, 
    Review, Order, OrderItem, Cart, CartItem, Favorite, Notification
)
from .forms import (
    ProductForm, ProductVariantForm, ProductSearchForm, 
    BulkProductActionForm, ReviewReplyForm, ProductStatusForm
)

# === VUES GÉNÉRALES ===

def home(request):
    """Page d'accueil"""
    featured_products = Product.objects.filter(
        is_featured=True, 
        is_active=True, 
        status='active',
        stock__gt=0
    )[:8]
    
    recent_products = Product.objects.filter(
        is_active=True, 
        status='active',
        stock__gt=0
    ).order_by('-created_at')[:12]
    
    categories = Category.objects.filter(is_active=True)[:8]
    
    context = {
        'featured_products': featured_products,
        'recent_products': recent_products,
        'categories': categories,
    }
    return render(request, 'store/home.html', context)

def product_list(request):
    """Liste des produits avec filtres"""
    products = Product.objects.filter(
        is_active=True,
        status='active',
        stock__gt=0
    ).select_related('category', 'seller')
    
    # Filtres
    query = request.GET.get('q')
    category_slug = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort_by = request.GET.get('sort', 'newest')
    
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query) |
            Q(brand__icontains=query)
        )
    
    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except:
            pass
    
    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except:
            pass
    
    # Tri
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'popular':
        products = products.order_by('-sales_count', '-views')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    else:  # newest
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': Category.objects.filter(is_active=True),
        'query': query,
        'selected_category': category_slug,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
    }
    return render(request, 'store/product_list.html', context)

def product_detail(request, slug):
    """Détail d'un produit"""
    product = get_object_or_404(
        Product.objects.select_related('category', 'seller'),
        slug=slug,
        is_active=True
    )
    
    # Incrémenter les vues
    product.increment_views()
    
    # Produits similaires
    similar_products = Product.objects.filter(
        category=product.category,
        is_active=True,
        status='active',
        stock__gt=0
    ).exclude(id=product.id)[:4]
    
    # Avis approuvés
    reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
    
    # Vérifier si l'utilisateur peut laisser un avis
    can_review = False
    if request.user.is_authenticated:
        # L'utilisateur doit avoir acheté le produit
        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            product=product,
            order__status='delivered'
        ).exists()
        
        # Et ne pas avoir déjà laissé d'avis
        has_reviewed = Review.objects.filter(
            user=request.user,
            product=product
        ).exists()
        
        can_review = has_purchased and not has_reviewed
    
    context = {
        'product': product,
        'similar_products': similar_products,
        'reviews': reviews,
        'can_review': can_review,
        'variants': product.variants.filter(is_active=True),
    }
    return render(request, 'store/product_detail.html', context)

# === VUES VENDEUR - GESTION DES PRODUITS ===

@method_decorator(login_required, name='dispatch')
class VendorProductListView(ListView):
    """Liste des produits du vendeur"""
    model = Product
    template_name = 'vendor/products/list.html'
    context_object_name = 'products'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'seller':
            raise PermissionDenied("Accès réservé aux vendeurs")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Product.objects.filter(seller=self.request.user).select_related('category')
        
        # Filtres
        form = ProductSearchForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data['q']:
                queryset = queryset.filter(
                    Q(name__icontains=form.cleaned_data['q']) |
                    Q(description__icontains=form.cleaned_data['q'])
                )
            
            if form.cleaned_data['category']:
                queryset = queryset.filter(category=form.cleaned_data['category'])
            
            if form.cleaned_data['status']:
                queryset = queryset.filter(status=form.cleaned_data['status'])
            
            if form.cleaned_data['stock_status']:
                stock_status = form.cleaned_data['stock_status']
                if stock_status == 'in_stock':
                    queryset = queryset.filter(stock__gt=5)
                elif stock_status == 'low_stock':
                    queryset = queryset.filter(stock__lte=5, stock__gt=0)
                elif stock_status == 'out_of_stock':
                    queryset = queryset.filter(stock=0)
        
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ProductSearchForm(self.request.GET)
        context['bulk_form'] = BulkProductActionForm()
        
        # Statistiques rapides
        products = Product.objects.filter(seller=self.request.user)
        context['stats'] = {
            'total': products.count(),
            'active': products.filter(status='active').count(),
            'pending': products.filter(status='pending').count(),
            'low_stock': products.filter(stock__lte=5, stock__gt=0).count(),
            'out_of_stock': products.filter(stock=0).count(),
        }
        
        return context

@method_decorator(login_required, name='dispatch')
class VendorProductCreateView(CreateView):
    """Création d'un nouveau produit"""
    model = Product
    form_class = ProductForm
    template_name = 'vendor/products/create.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'seller':
            raise PermissionDenied("Accès réservé aux vendeurs")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request, 
            f"Produit '{form.instance.name}' créé avec succès ! "
            "Il sera visible après modération."
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('vendor:products')

@method_decorator(login_required, name='dispatch')
class VendorProductUpdateView(UpdateView):
    """Modification d'un produit"""
    model = Product
    form_class = ProductForm
    template_name = 'vendor/products/edit.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'seller':
            raise PermissionDenied("Accès réservé aux vendeurs")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Remettre en modération si changements importants
        if form.has_changed() and any(field in form.changed_data for field in ['name', 'description', 'price']):
            form.instance.status = 'pending'
            messages.info(
                self.request,
                "Votre produit a été remis en modération suite aux modifications importantes."
            )
        
        messages.success(self.request, f"Produit '{form.instance.name}' mis à jour avec succès !")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('vendor:products')

@method_decorator(login_required, name='dispatch')
class VendorProductDeleteView(DeleteView):
    """Suppression d'un produit"""
    model = Product
    template_name = 'vendor/products/delete.html'
    success_url = reverse_lazy('vendor:products')

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'seller':
            raise PermissionDenied("Accès réservé aux vendeurs")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)

    def delete(self, request, *args, **kwargs):
        product = self.get_object()
        product_name = product.name
        
        # Vérifier s'il y a des commandes en cours
        pending_orders = OrderItem.objects.filter(
            product=product,
            order__status__in=['pending', 'confirmed', 'processing', 'shipped']
        ).exists()
        
        if pending_orders:
            messages.error(
                request,
                f"Impossible de supprimer '{product_name}'. "
                "Il y a des commandes en cours pour ce produit."
            )
            return redirect('vendor:products')
        
        messages.success(request, f"Produit '{product_name}' supprimé avec succès.")
        return super().delete(request, *args, **kwargs)

@login_required
@require_POST
def bulk_product_action(request):
    """Actions en lot sur les produits"""
    if request.user.user_type != 'seller':
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    
    form = BulkProductActionForm(request.POST)
    product_ids = request.POST.getlist('product_ids')
    
    if not form.is_valid() or not product_ids:
        return JsonResponse({'error': 'Données invalides'}, status=400)
    
    products = Product.objects.filter(
        id__in=product_ids,
        seller=request.user
    )
    
    action = form.cleaned_data['action']
    count = products.count()
    
    if action == 'activate':
        products.update(is_active=True)
        message = f"{count} produit(s) activé(s)"
    
    elif action == 'deactivate':
        products.update(is_active=False)
        message = f"{count} produit(s) désactivé(s)"
    
    elif action == 'delete':
        # Vérifier les commandes en cours
        pending_orders = OrderItem.objects.filter(
            product__in=products,
            order__status__in=['pending', 'confirmed', 'processing', 'shipped']
        ).exists()
        
        if pending_orders:
            return JsonResponse({
                'error': 'Certains produits ont des commandes en cours'
            }, status=400)
        
        products.delete()
        message = f"{count} produit(s) supprimé(s)"
    
    elif action == 'update_category':
        new_category = form.cleaned_data['new_category']
        if new_category:
            products.update(category=new_category)
            message = f"{count} produit(s) déplacé(s) vers {new_category.name}"
        else:
            return JsonResponse({'error': 'Catégorie requise'}, status=400)
    
    else:
        return JsonResponse({'error': 'Action non supportée'}, status=400)
    
    return JsonResponse({'success': True, 'message': message})

@login_required
def product_quick_edit(request, product_id):
    """Édition rapide d'un produit (AJAX)"""
    if request.user.user_type != 'seller':
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        field = data.get('field')
        value = data.get('value')
        
        # Champs autorisés pour l'édition rapide
        allowed_fields = ['name', 'price', 'stock', 'is_active']
        
        if field not in allowed_fields:
            return JsonResponse({'error': 'Champ non autorisé'}, status=400)
        
        try:
            if field == 'price':
                value = Decimal(value)
                if value <= 0:
                    raise ValueError("Prix invalide")
            elif field == 'stock':
                value = int(value)
                if value < 0:
                    raise ValueError("Stock invalide")
            elif field == 'is_active':
                value = bool(value)
            
            setattr(product, field, value)
            product.save(update_fields=[field, 'updated_at'])
            
            return JsonResponse({
                'success': True,
                'message': f'{field.title()} mis à jour'
            })
            
        except (ValueError, TypeError) as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@login_required
def product_duplicate(request, product_id):
    """Dupliquer un produit"""
    if request.user.user_type != 'seller':
        raise PermissionDenied("Accès réservé aux vendeurs")
    
    original = get_object_or_404(Product, id=product_id, seller=request.user)
    
    # Créer une copie
    duplicate = Product.objects.get(id=original.id)
    duplicate.pk = None
    duplicate.name = f"{original.name} (Copie)"
    duplicate.slug = ""  # Sera généré automatiquement
    duplicate.status = 'draft'
    duplicate.views = 0
    duplicate.sales_count = 0
    duplicate.favorites_count = 0
    duplicate.save()
    
    messages.success(
        request,
        f"Produit dupliqué avec succès ! "
        f"Vous pouvez maintenant modifier '{duplicate.name}'."
    )
    
    return redirect('vendor:product_edit', pk=duplicate.pk)

# === GESTION DES VARIANTES ===

@login_required
def product_variants(request, product_id):
    """Gestion des variantes d'un produit"""
    if request.user.user_type != 'seller':
        raise PermissionDenied("Accès réservé aux vendeurs")
    
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    variants = product.variants.all()
    
    if request.method == 'POST':
        form = ProductVariantForm(request.POST, request.FILES)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = product
            variant.save()
            messages.success(request, f"Variante '{variant.name}' ajoutée avec succès !")
            return redirect('vendor:product_variants', product_id=product.id)
    else:
        form = ProductVariantForm()
    
    context = {
        'product': product,
        'variants': variants,
        'form': form,
    }
    return render(request, 'vendor/products/variants.html', context)

@login_required
@require_POST
def delete_variant(request, variant_id):
    """Supprimer une variante"""
    if request.user.user_type != 'seller':
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    
    variant = get_object_or_404(
        ProductVariant,
        id=variant_id,
        product__seller=request.user
    )
    
    variant_name = variant.name
    variant.delete()
    
    return JsonResponse({
        'success': True,
        'message': f"Variante '{variant_name}' supprimée"
    })

# === GESTION DES AVIS ===

@login_required
def vendor_reviews(request):
    """Liste des avis reçus par le vendeur"""
    if request.user.user_type != 'seller':
        raise PermissionDenied("Accès réservé aux vendeurs")
    
    reviews = Review.objects.filter(
        product__seller=request.user
    ).select_related('product', 'user').order_by('-created_at')
    
    # Filtres
    status_filter = request.GET.get('status')
    if status_filter == 'pending':
        reviews = reviews.filter(is_approved=False)
    elif status_filter == 'approved':
        reviews = reviews.filter(is_approved=True)
    elif status_filter == 'replied':
        reviews = reviews.exclude(seller_reply='')
    elif status_filter == 'unreplied':
        reviews = reviews.filter(seller_reply='')
    
    # Pagination
    paginator = Paginator(reviews, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiques
    stats = {
        'total': reviews.count(),
        'pending': reviews.filter(is_approved=False).count(),
        'average_rating': reviews.filter(is_approved=True).aggregate(
            avg=Avg('rating')
        )['avg'] or 0,
        'unreplied': reviews.filter(seller_reply='').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'status_filter': status_filter,
    }
    return render(request, 'vendor/reviews/list.html', context)

@login_required
def reply_to_review(request, review_id):
    """Répondre à un avis"""
    if request.user.user_type != 'seller':
        raise PermissionDenied("Accès réservé aux vendeurs")
    
    review = get_object_or_404(
        Review,
        id=review_id,
        product__seller=request.user
    )
    
    if request.method == 'POST':
        form = ReviewReplyForm(request.POST)
        if form.is_valid():
            review.seller_reply = form.cleaned_data['reply']
            review.seller_reply_date = timezone.now()
            review.save()
            
            messages.success(request, "Réponse ajoutée avec succès !")
            return redirect('vendor:reviews')
    else:
        form = ReviewReplyForm(initial={'reply': review.seller_reply})
    
    context = {
        'review': review,
        'form': form,
    }
    return render(request, 'vendor/reviews/reply.html', context)

# === STATISTIQUES PRODUITS ===

@login_required
def product_analytics(request, product_id):
    """Analytiques détaillées d'un produit"""
    if request.user.user_type != 'seller':
        raise PermissionDenied("Accès réservé aux vendeurs")
    
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    # Données pour les graphiques
    from django.db.models.functions import TruncDate
    from datetime import datetime, timedelta
    
    # Vues par jour (30 derniers jours)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Ventes par jour
    sales_data = OrderItem.objects.filter(
        product=product,
        created_at__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        quantity=Sum('quantity'),
        revenue=Sum('total_price')
    ).order_by('date')
    
    context = {
        'product': product,
        'sales_data': list(sales_data),
        'total_revenue': OrderItem.objects.filter(
            product=product,
            order__status='delivered'
        ).aggregate(total=Sum('total_price'))['total'] or 0,
        'total_orders': OrderItem.objects.filter(product=product).count(),
        'conversion_rate': (product.sales_count / product.views * 100) if product.views > 0 else 0,
    }
    return render(request, 'vendor/products/analytics.html', context)

# === UTILITAIRES ===

@login_required
def categories_autocomplete(request):
    """Autocomplétion pour les catégories"""
    query = request.GET.get('q', '')
    categories = Category.objects.filter(
        name__icontains=query,
        is_active=True
    )[:10]
    
    results = [{'id': cat.id, 'name': cat.name} for cat in categories]
    return JsonResponse({'results': results})

@login_required
def product_status_update(request, product_id):
    """Mettre à jour le statut d'un produit"""
    if request.user.user_type != 'seller':
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        form = ProductStatusForm(request.POST)
        if form.is_valid():
            old_status = product.status
            product.status = form.cleaned_data['status']
            product.save()
            
            # Créer une notification si nécessaire
            if old_status != product.status:
                Notification.objects.create(
                    user=request.user,
                    type='product_updated',
                    title=f"Statut du produit mis à jour",
                    message=f"Le statut de '{product.name}' est passé de {old_status} à {product.status}",
                    action_url=product.get_absolute_url(),
                    action_text="Voir le produit"
                )
            
            return JsonResponse({
                'success': True,
                'message': f"Statut mis à jour : {product.get_status_display()}"
            })
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

# === GESTION DES IMAGES ===

@login_required
@require_POST
def upload_product_image(request, product_id):
    """Upload d'image via AJAX"""
    if request.user.user_type != 'seller':
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if 'image' not in request.FILES:
        return JsonResponse({'error': 'Aucune image fournie'}, status=400)
    
    image = request.FILES['image']
    slot = request.POST.get('slot', '1')  # image1, image2, etc.
    
    # Validation
    if image.size > 5 * 1024 * 1024:  # 5MB
        return JsonResponse({'error': 'Image trop volumineuse (max 5MB)'}, status=400)
    
    # Sauvegarder l'image
    setattr(product, f'image{slot}', image)
    product.save()
    
    return JsonResponse({
        'success': True,
        'image_url': getattr(product, f'image{slot}').url,
        'message': 'Image uploadée avec succès'
    })

@login_required
@require_POST
def delete_product_image(request, product_id):
    """Supprimer une image de produit"""
    if request.user.user_type != 'seller':
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    slot = request.POST.get('slot')
    
    if slot in ['1', '2', '3', '4', '5']:
        image_field = f'image{slot}'
        if hasattr(product, image_field):
            # Supprimer le fichier
            image = getattr(product, image_field)
            if image:
                image.delete()
            
            # Vider le champ
            setattr(product, image_field, None)
            product.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Image supprimée'
            })
    
    return JsonResponse({'error': 'Slot invalide'}, status=400)

# === GESTION DU STOCK ===

@login_required
def stock_management(request):
    """Gestion globale du stock"""
    if request.user.user_type != 'seller':
        raise PermissionDenied("Accès réservé aux vendeurs")
    
    products = Product.objects.filter(seller=request.user).order_by('stock')
    
    # Filtrer par statut de stock
    stock_filter = request.GET.get('filter')
    if stock_filter == 'low':
        products = products.filter(stock__lte=5, stock__gt=0)
    elif stock_filter == 'out':
        products = products.filter(stock=0)
    elif stock_filter == 'good':
        products = products.filter(stock__gt=5)
    
    # Pagination
    paginator = Paginator(products, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiques
    stats = {
        'total_products': Product.objects.filter(seller=request.user).count(),
        'low_stock': Product.objects.filter(seller=request.user, stock__lte=5, stock__gt=0).count(),
        'out_of_stock': Product.objects.filter(seller=request.user, stock=0).count(),
        'total_stock_value': Product.objects.filter(seller=request.user).aggregate(
            total=Sum('stock')
        )['total'] or 0,
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'stock_filter': stock_filter,
    }
    return render(request, 'vendor/stock/management.html', context)

@login_required
@require_POST
def update_stock(request, product_id):
    """Mettre à jour le stock d'un produit"""
    if request.user.user_type != 'seller':
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    try:
        new_stock = int(request.POST.get('stock', 0))
        if new_stock < 0:
            raise ValueError("Stock négatif non autorisé")
        
        old_stock = product.stock
        product.stock = new_stock
        product.save()
        
        # Notification si stock faible
        if new_stock <= product.low_stock_threshold and old_stock > product.low_stock_threshold:
            Notification.objects.create(
                user=request.user,
                type='stock_low',
                title="Stock faible",
                message=f"Le stock de '{product.name}' est faible ({new_stock} restant)",
                action_url=reverse('vendor:product_edit', kwargs={'pk': product.pk}),
                action_text="Gérer le stock"
            )
        
        return JsonResponse({
            'success': True,
            'message': f"Stock mis à jour : {new_stock}",
            'new_stock': new_stock,
            'is_low_stock': new_stock <= product.low_stock_threshold
        })
        
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Stock invalide'}, status=400)

# === ERREURS ===

def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)