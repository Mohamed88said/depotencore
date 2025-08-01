from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, Http404
from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, TemplateView, View
from django.urls import reverse_lazy, reverse
from django.core.exceptions import PermissionDenied
from django.db import transaction
from decimal import Decimal
import json
import requests
import uuid
from datetime import timedelta

from .models import (
    Product, Category, Cart, CartItem, Order, OrderItem, Address, ShippingOption,
    Favorite, Review, Notification, ProductView, ProductRequest, Conversation, Message,
    SellerRating, SellerProfile, Subscription, QRDeliveryCode, DeliveryAssignment,
    DeliveryProfile, DeliveryRating
)
from .forms import (
    ProductForm, AddressForm, ReviewForm, CartItemForm, ProductRequestForm, ReportForm,
    CheckoutForm, DiscountForm, MessageForm, ReviewReplyForm, ProductRequestResponseForm,
    SellerRatingForm, SellerProfileForm
)
from .utils import get_sales_metrics, generate_qr_code_image, calculate_delivery_distance, calculate_commission
from marketing.models import PromoCode, LoyaltyPoint
from admin_panel.models import Report

def home(request):
    """Page d'accueil"""
    featured_products = Product.objects.filter(
        is_sold=False, sold_out=False, stock__gt=0
    ).order_by('-views')[:8]
    
    categories = Category.objects.all()[:6]
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
    }
    return render(request, 'home.html', context)

def product_list(request):
    """Liste des produits avec filtres"""
    products = Product.objects.filter(is_sold=False, sold_out=False, stock__gt=0)
    
    # Filtres
    query = request.GET.get('q')
    category = request.GET.get('category')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    size_filter = request.GET.get('size')
    brand_filter = request.GET.get('brand')
    color_filter = request.GET.get('color')
    material_filter = request.GET.get('material')
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(brand__icontains=query)
        )
    
    if category:
        products = products.filter(category__name=category)
    
    if price_min:
        products = products.filter(price__gte=price_min)
    
    if price_max:
        products = products.filter(price__lte=price_max)
    
    if size_filter:
        products = products.filter(size=size_filter)
    
    if brand_filter:
        products = products.filter(brand__icontains=brand_filter)
    
    if color_filter:
        products = products.filter(color__icontains=color_filter)
    
    if material_filter:
        products = products.filter(material__icontains=material_filter)
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    categories = Category.objects.all()
    product_sizes = Product.SIZE_CHOICES
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'product_sizes': product_sizes,
        'query': query,
        'selected_category': category,
        'price_min': price_min,
        'price_max': price_max,
        'size_filter': size_filter,
        'brand_filter': brand_filter,
        'color_filter': color_filter,
        'material_filter': material_filter,
    }
    return render(request, 'store/product_list.html', context)

def product_detail(request, product_id):
    """Détail d'un produit"""
    product = get_object_or_404(Product, id=product_id)
    
    # Incrémenter les vues
    product.views += 1
    product.save()
    
    # Enregistrer vue pour statistiques
    today = timezone.now().date()
    product_view, created = ProductView.objects.get_or_create(
        product=product,
        view_date=today,
        defaults={'view_count': 1}
    )
    if not created:
        product_view.view_count += 1
        product_view.save()
    
    # Avis approuvés
    reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
    
    # Vérifier si l'utilisateur peut laisser un avis
    can_review = False
    has_reviewed = False
    if request.user.is_authenticated:
        has_reviewed = Review.objects.filter(product=product, user=request.user).exists()
        # Peut laisser un avis s'il a acheté le produit et ne l'a pas encore noté
        can_review = (
            not has_reviewed and
            OrderItem.objects.filter(
                product=product,
                order__user=request.user,
                order__status='delivered'
            ).exists()
        )
    
    # Traitement formulaire avis
    if request.method == 'POST' and can_review:
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        if rating:
            Review.objects.create(
                product=product,
                user=request.user,
                rating=int(rating),
                comment=comment
            )
            messages.success(request, "Votre avis a été soumis avec succès.")
            return redirect('store:product_detail', product_id=product.id)
    
    # Produits similaires
    similar_products = Product.objects.filter(
        category=product.category,
        is_sold=False,
        sold_out=False,
        stock__gt=0
    ).exclude(id=product.id)[:4]
    
    # Produits recommandés
    recommended_products = Product.objects.filter(
        is_sold=False,
        sold_out=False,
        stock__gt=0
    ).exclude(id=product.id).order_by('-views')[:4]
    
    # Produits populaires
    popular_products = Product.objects.filter(
        is_sold=False,
        sold_out=False,
        stock__gt=0
    ).exclude(id=product.id).order_by('-sales_count')[:4]
    
    # Vérifier si c'est un favori
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, product=product).exists()
    
    # Compter les favoris
    favorite_count = Favorite.objects.filter(product=product).count()
    
    # Note moyenne
    average_rating = product.average_rating
    
    context = {
        'product': product,
        'reviews': reviews,
        'can_review': can_review,
        'has_reviewed': has_reviewed,
        'similar_products': similar_products,
        'recommended_products': recommended_products,
        'popular_products': popular_products,
        'is_favorite': is_favorite,
        'favorite_count': favorite_count,
        'average_rating': average_rating,
    }
    return render(request, 'store/product_detail.html', context)

@login_required
def cart(request):
    """Panier de l'utilisateur"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    if not cart_items:
        return render(request, 'store/cart.html', {'cart_items': []})
    
    subtotal = cart.subtotal
    shipping_cost = Decimal('5.00')  # Coût fixe pour l'exemple
    total = subtotal + shipping_cost
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total,
    }
    return render(request, 'store/cart.html', context)

@login_required
def add_to_cart(request, product_id):
    """Ajouter un produit au panier"""
    product = get_object_or_404(Product, id=product_id)
    
    if product.is_sold_out:
        messages.error(request, "Ce produit n'est plus disponible.")
        return redirect('store:product_detail', product_id=product.id)
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f"{product.name} ajouté au panier.")
        else:
            messages.error(request, "Stock insuffisant.")
    else:
        messages.success(request, f"{product.name} ajouté au panier.")
    
    # Retourner JSON pour les requêtes AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': cart.total_items,
            'message': f"{product.name} ajouté au panier."
        })
    
    return redirect('store:product_detail', product_id=product.id)

@login_required
def update_cart(request, item_id):
    """Mettre à jour la quantité d'un article du panier"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            cart_item.delete()
            messages.success(request, "Article supprimé du panier.")
        elif quantity <= cart_item.product.stock:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, "Quantité mise à jour.")
        else:
            messages.error(request, "Stock insuffisant.")
    
    return redirect('store:cart')

@login_required
def remove_from_cart(request, item_id):
    """Supprimer un article du panier"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f"{product_name} supprimé du panier.")
    return redirect('store:cart')

@login_required
def checkout(request):
    """Page de checkout"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    if not cart_items:
        messages.warning(request, "Votre panier est vide.")
        return redirect('store:cart')
    
    # Calculer les totaux
    subtotal = cart.subtotal
    shipping_cost = Decimal('5.00')
    discount_amount = Decimal('0.00')
    
    # Récupérer la réduction de session
    if 'applied_discount' in request.session:
        discount_amount = Decimal(str(request.session['applied_discount']))
    
    total = subtotal + shipping_cost - discount_amount
    
    # Adresses de l'utilisateur
    addresses = Address.objects.filter(user=request.user)
    
    # Options de livraison
    shipping_options = ShippingOption.objects.filter(is_active=True)
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'discount_amount': discount_amount,
        'total': total,
        'addresses': addresses,
        'shipping_options': shipping_options,
    }
    return render(request, 'store/checkout.html', context)

@login_required
def process_payment(request):
    """Traiter le paiement"""
    if request.method != 'POST':
        return redirect('store:checkout')
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    if not cart_items:
        messages.error(request, "Votre panier est vide.")
        return redirect('store:cart')
    
    try:
        with transaction.atomic():
            # Récupérer les données du formulaire
            delivery_mode = request.POST.get('delivery_mode', 'home')
            preferred_payment_method = request.POST.get('preferred_payment_method', 'cash')
            commission_payer = request.POST.get('commission_payer', 'customer')
            address_mode = request.POST.get('address_mode', 'existing')
            shipping_option_id = request.POST.get('shipping_option')
            special_instructions = request.POST.get('special_instructions', '')
            
            # Géolocalisation
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            location_description = request.POST.get('location_description', '')
            
            # Gestion de l'adresse
            shipping_address = None
            if delivery_mode == 'home':
                if address_mode == 'existing':
                    address_id = request.POST.get('address')
                    if address_id:
                        shipping_address = get_object_or_404(Address, id=address_id, user=request.user)
                else:
                    # Créer nouvelle adresse
                    shipping_address = Address.objects.create(
                        user=request.user,
                        full_name=request.POST.get('full_name'),
                        street_address=request.POST.get('street_address'),
                        city=request.POST.get('city'),
                        postal_code=request.POST.get('postal_code'),
                        country=request.POST.get('country', 'Guinée'),
                        phone_number=request.POST.get('phone_number', ''),
                    )
            
            # Option de livraison
            shipping_option = None
            if shipping_option_id:
                shipping_option = get_object_or_404(ShippingOption, id=shipping_option_id)
            
            # Calculer les totaux
            subtotal = cart.subtotal
            shipping_cost = shipping_option.cost if shipping_option else Decimal('5.00')
            discount_amount = Decimal('0.00')
            
            # Appliquer réduction de session
            if 'applied_discount' in request.session:
                discount_amount = Decimal(str(request.session['applied_discount']))
            
            total = subtotal + shipping_cost - discount_amount
            
            # Créer la commande
            order = Order.objects.create(
                user=request.user,
                total=total,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                discount_amount=discount_amount,
                shipping_address=shipping_address,
                shipping_option=shipping_option,
                status='pending',
                payment_method='cod',  # Toujours paiement à la livraison
                delivery_mode=delivery_mode,
                preferred_payment_method=preferred_payment_method,
                commission_payer=commission_payer,
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None,
                location_description=location_description,
            )
            
            # Créer les OrderItems
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.discounted_price,
                    seller=cart_item.product.seller
                )
                
                # Réduire le stock
                cart_item.product.stock -= cart_item.quantity
                cart_item.product.save()
            
            # Créer le QR Code de livraison
            delivery_address_text = ""
            if shipping_address:
                delivery_address_text = f"{shipping_address.full_name}, {shipping_address.street_address}, {shipping_address.city}, {shipping_address.postal_code}"
            elif delivery_mode == 'pickup':
                delivery_address_text = "Retrait en boutique"
            
            qr_code = QRDeliveryCode.objects.create(
                order=order,
                delivery_address=delivery_address_text,
                delivery_mode=delivery_mode,
                preferred_payment_method=preferred_payment_method,
                special_instructions=special_instructions,
                expires_at=timezone.now() + timedelta(days=7)
            )
            
            # Vider le panier
            cart_items.delete()
            
            # Nettoyer la session
            if 'applied_discount' in request.session:
                del request.session['applied_discount']
            
            # Créer points de fidélité
            points_earned = int(total // 10)  # 1 point par 10€
            if points_earned > 0:
                LoyaltyPoint.objects.create(
                    user=request.user,
                    points=points_earned,
                    description=f"Commande #{order.id}"
                )
            
            # Notification vendeur
            sellers = set()
            for item in order.items.all():
                if item.seller and item.seller not in sellers:
                    Notification.objects.create(
                        user=item.seller,
                        notification_type='new_order',
                        message=f"Nouvelle commande #{order.id} reçue.",
                        related_object_id=order.id
                    )
                    sellers.add(item.seller)
            
            messages.success(request, f"Commande #{order.id} créée avec succès!")
            return redirect('store:payment_success', order_id=order.id)
            
    except Exception as e:
        messages.error(request, f"Erreur lors du traitement de la commande: {str(e)}")
        return redirect('store:checkout')

def payment_success(request, order_id):
    """Page de succès après paiement"""
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier que l'utilisateur peut voir cette commande
    if request.user.is_authenticated:
        if order.user != request.user and not request.user.is_staff:
            raise PermissionDenied("Vous n'êtes pas autorisé à voir cette commande.")
    
    context = {
        'order': order,
        'message': "Votre commande a été créée avec succès. Vous recevrez un QR Code pour le paiement à la livraison."
    }
    return render(request, 'store/payment_success.html', context)

@login_required
def add_address(request):
    """Ajouter une nouvelle adresse"""
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Adresse ajoutée avec succès.")
            
            # Redirection selon le paramètre next
            next_url = request.GET.get('next', reverse('accounts:profile'))
            return redirect(next_url)
    else:
        form = AddressForm()
    
    next_url = request.GET.get('next', reverse('accounts:profile'))
    return render(request, 'store/add_address.html', {'form': form, 'next_url': next_url})

@login_required
def order_history(request):
    """Historique des commandes"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj,
    }
    return render(request, 'store/order_history.html', context)

@login_required
def order_detail(request, order_id):
    """Détail d'une commande"""
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier les permissions
    if order.user != request.user and not request.user.is_staff:
        if not (request.user.user_type == 'seller' and 
                order.items.filter(product__seller=request.user).exists()):
            raise PermissionDenied("Vous n'êtes pas autorisé à voir cette commande.")
    
    order_items = order.items.all()
    
    # Formulaire de retour pour les acheteurs
    return_form = None
    return_requests = []
    if request.user == order.user and order.status == 'delivered':
        from returns.forms import ReturnRequestForm
        return_form = ReturnRequestForm()
        return_requests = order.return_requests.all()
    
    context = {
        'order': order,
        'order_items': order_items,
        'return_form': return_form,
        'return_requests': return_requests,
    }
    return render(request, 'store/order_detail.html', context)

@login_required
def favorites(request):
    """Liste des favoris"""
    favorites = Favorite.objects.filter(user=request.user).select_related('product')
    
    context = {
        'favorites': favorites,
    }
    return render(request, 'store/favorites.html', context)

@login_required
def toggle_favorite(request, product_id):
    """Ajouter/retirer des favoris"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})
    
    product = get_object_or_404(Product, id=product_id)
    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if created:
        action = 'added'
        message = f"{product.name} ajouté aux favoris."
    else:
        favorite.delete()
        action = 'removed'
        message = f"{product.name} retiré des favoris."
    
    favorite_count = Favorite.objects.filter(product=product).count()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'action': action,
            'message': message,
            'favorite_count': favorite_count
        })
    
    messages.success(request, message)
    return redirect('store:product_detail', product_id=product.id)

@login_required
def notifications(request):
    """Page des notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'notifications': notifications,
    }
    return render(request, 'store/notifications.html', context)

@login_required
def mark_all_notifications_read(request):
    """Marquer toutes les notifications comme lues"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "Toutes les notifications ont été marquées comme lues.")
    return redirect('store:notifications')

@login_required
def product_request(request, product_id):
    """Demander un produit en rupture"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductRequestForm(request.POST, user=request.user)
        if form.is_valid():
            product_request = form.save(commit=False)
            product_request.product = product
            if request.user.is_authenticated:
                product_request.user = request.user
            product_request.save()
            
            # Notification vendeur
            Notification.objects.create(
                user=product.seller,
                notification_type='product_request',
                message=f"Nouvelle demande pour {product.name}",
                related_object_id=product.id
            )
            
            messages.success(request, "Votre demande a été envoyée au vendeur.")
            return redirect('store:product_detail', product_id=product.id)
    else:
        form = ProductRequestForm(user=request.user)
    
    context = {
        'form': form,
        'product': product,
    }
    return render(request, 'store/request_product.html', context)

@login_required
def apply_promo_code(request):
    """Appliquer un code promo"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})
    
    try:
        data = json.loads(request.body)
        promo_code = data.get('promo_code', '').strip().upper()
        
        if not promo_code:
            return JsonResponse({'success': False, 'message': 'Code promo requis'})
        
        # Vérifier le panier
        cart, created = Cart.objects.get_or_create(user=request.user)
        if not cart.items.exists():
            return JsonResponse({'success': False, 'message': 'Panier vide'})
        
        # Chercher le code promo
        try:
            promo = PromoCode.objects.get(code=promo_code)
        except PromoCode.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Code promo introuvable.'})
        
        # Vérifier validité
        if not promo.is_valid(request.user):
            return JsonResponse({'success': False, 'message': 'Code promo expiré ou non valide.'})
        
        # Calculer la réduction
        subtotal = cart.subtotal
        shipping_cost = Decimal('5.00')
        discount_amount = subtotal * (promo.discount_percentage / Decimal('100'))
        new_total = subtotal + shipping_cost - discount_amount
        
        # Sauvegarder en session
        request.session['applied_discount'] = float(discount_amount)
        request.session['promo_code'] = promo_code
        
        return JsonResponse({
            'success': True,
            'message': f'Code promo {promo_code} appliqué!',
            'discount_amount': float(discount_amount),
            'new_total': float(new_total)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Données invalides'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erreur: {str(e)}'})

# === VUES QR CODE ET LIVRAISON ===

def view_qr_code(request, order_id):
    """Afficher le QR Code d'une commande (vendeur)"""
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier permissions (vendeur ou staff)
    if not (request.user.is_staff or 
            (request.user.user_type == 'seller' and 
             order.items.filter(product__seller=request.user).exists())):
        return HttpResponseForbidden("Accès non autorisé")
    
    # Récupérer ou créer le QR Code
    qr_code, created = QRDeliveryCode.objects.get_or_create(
        order=order,
        defaults={
            'delivery_address': f"{order.shipping_address.street_address}, {order.shipping_address.city}" if order.shipping_address else "Retrait en boutique",
            'delivery_mode': order.delivery_mode,
            'preferred_payment_method': order.preferred_payment_method,
            'expires_at': timezone.now() + timedelta(days=7)
        }
    )
    
    # Générer l'image QR Code
    qr_url = request.build_absolute_uri(qr_code.qr_url)
    qr_image = generate_qr_code_image(qr_url)
    
    # Calculer distance et commission
    distance_km = calculate_delivery_distance(order)
    commission = calculate_commission(distance_km)
    
    # Compter livreurs disponibles
    available_couriers = DeliveryProfile.objects.filter(
        is_available=True,
        user__is_active=True
    ).count()
    
    context = {
        'order': order,
        'qr_code': qr_code,
        'qr_image': qr_image,
        'qr_url': qr_url,
        'distance_km': distance_km,
        'commission': commission,
        'available_couriers': available_couriers,
    }
    return render(request, 'store/qr_code_view.html', context)

def scan_qr_payment(request, code):
    """Scanner un QR Code pour paiement"""
    try:
        qr_code = QRDeliveryCode.objects.get(code=code)
    except QRDeliveryCode.DoesNotExist:
        return render(request, 'store/qr_not_found.html')
    
    # Vérifier expiration
    if qr_code.is_expired:
        return render(request, 'store/qr_expired.html', {'qr_code': qr_code})
    
    # Vérifier si déjà utilisé
    if qr_code.is_used or qr_code.order.status == 'delivered':
        return render(request, 'store/already_paid.html', {'order': qr_code.order})
    
    order = qr_code.order
    
    # Informations de livraison
    delivery_info = {
        'mode': qr_code.delivery_mode,
        'address': qr_code.delivery_address,
        'instructions': qr_code.special_instructions,
    }
    
    # Méthodes de paiement disponibles
    can_pay_cash = True
    can_pay_card = True  # Toujours disponible
    can_pay_paypal = True  # Toujours disponible
    
    context = {
        'order': order,
        'qr_code': qr_code,
        'delivery_info': delivery_info,
        'can_pay_cash': can_pay_cash,
        'can_pay_card': can_pay_card,
        'can_pay_paypal': can_pay_paypal,
    }
    return render(request, 'store/qr_payment_process.html', context)

def process_qr_payment(request, code):
    """Traiter le paiement via QR Code"""
    if request.method != 'POST':
        return redirect('store:scan_qr_payment', code=code)
    
    try:
        qr_code = QRDeliveryCode.objects.get(code=code)
    except QRDeliveryCode.DoesNotExist:
        return render(request, 'store/qr_not_found.html')
    
    if qr_code.is_expired or qr_code.is_used:
        return render(request, 'store/qr_expired.html', {'qr_code': qr_code})
    
    order = qr_code.order
    payment_method = request.POST.get('payment_method')
    
    try:
        with transaction.atomic():
            if payment_method == 'cash':
                # Vérifier confirmations
                customer_confirms = request.POST.get('customer_confirms') == 'true'
                delivery_confirms = request.POST.get('delivery_confirms') == 'true'
                
                if not (customer_confirms and delivery_confirms):
                    messages.error(request, "Les deux parties doivent confirmer le paiement.")
                    return redirect('store:scan_qr_payment', code=code)
                
                # Marquer comme payé
                order.status = 'delivered'
                order.save()
                
                qr_code.mark_as_used()
                
                # Notification client
                Notification.objects.create(
                    user=order.user,
                    notification_type='order_delivered',
                    message=f"Votre commande #{order.id} a été livrée et payée.",
                    related_object_id=order.id
                )
                
                messages.success(request, "Paiement en espèces confirmé!")
                return redirect('store:delivery_confirmation', code=code)
                
            elif payment_method == 'card':
                # Redirection vers Stripe
                return redirect('store:stripe_payment', code=code)
                
            elif payment_method == 'paypal':
                # Redirection vers PayPal
                return redirect('store:paypal_payment', code=code)
            
            else:
                messages.error(request, "Méthode de paiement non valide.")
                return redirect('store:scan_qr_payment', code=code)
                
    except Exception as e:
        messages.error(request, f"Erreur lors du paiement: {str(e)}")
        return redirect('store:scan_qr_payment', code=code)

def delivery_confirmation(request, code):
    """Page de confirmation de livraison"""
    try:
        qr_code = QRDeliveryCode.objects.get(code=code)
    except QRDeliveryCode.DoesNotExist:
        return render(request, 'store/qr_not_found.html')
    
    if not qr_code.is_used:
        return redirect('store:scan_qr_payment', code=code)
    
    order = qr_code.order
    
    context = {
        'order': order,
        'qr_code': qr_code,
    }
    return render(request, 'store/delivery_confirmation.html', context)

def payment_verification(request, order_id):
    """Vérifier le statut de paiement"""
    order = get_object_or_404(Order, id=order_id)
    
    payment_status = {
        'is_paid': order.status == 'delivered',
        'total': order.total,
        'qr_used': hasattr(order, 'qr_code') and order.qr_code.is_used if hasattr(order, 'qr_code') else False,
    }
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse(payment_status)
    
    context = {
        'order': order,
        'payment_status': payment_status,
    }
    return render(request, 'store/payment_verification.html', context)

# === VUES VENDEUR ===

@login_required
def vendor_pending_orders(request):
    """Commandes en attente pour le vendeur"""
    if request.user.user_type != 'seller':
        return HttpResponseForbidden("Accès réservé aux vendeurs")
    
    # Commandes avec QR Code généré mais pas encore assignées
    pending_orders = Order.objects.filter(
        items__product__seller=request.user,
        status__in=['pending', 'processing'],
        qr_code__isnull=False
    ).distinct().order_by('-created_at')
    
    context = {
        'pending_orders': pending_orders,
    }
    return render(request, 'store/vendor_pending_orders.html', context)

@login_required
def assign_delivery_choice(request, order_id):
    """Choisir le mode de livraison pour une commande"""
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier permissions
    if not (request.user.is_staff or 
            (request.user.user_type == 'seller' and 
             order.items.filter(product__seller=request.user).exists())):
        return HttpResponseForbidden("Accès non autorisé")
    
    if request.method == 'POST':
        delivery_choice = request.POST.get('delivery_choice')
        
        if delivery_choice == 'self':
            # Le vendeur livre lui-même
            order.status = 'shipped'
            order.save()
            messages.success(request, "Vous avez choisi de livrer vous-même cette commande.")
            return redirect('store:vendor_pending_orders')
            
        elif delivery_choice == 'courier':
            # Assigner à un livreur
            return redirect('store:select_delivery_person', order_id=order.id)
    
    # Calculer distance et commission
    distance_km = calculate_delivery_distance(order)
    commission = calculate_commission(distance_km)
    available_couriers = DeliveryProfile.objects.filter(is_available=True).count()
    
    context = {
        'order': order,
        'distance_km': distance_km,
        'commission': commission,
        'available_couriers': available_couriers,
    }
    return render(request, 'store/delivery_choice.html', context)

@login_required
def select_delivery_person(request, order_id):
    """Sélectionner un livreur spécifique"""
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier permissions
    if not (request.user.is_staff or 
            (request.user.user_type == 'seller' and 
             order.items.filter(product__seller=request.user).exists())):
        return HttpResponseForbidden("Accès non autorisé")
    
    if request.method == 'POST':
        courier_id = request.POST.get('courier_id')
        vendor_instructions = request.POST.get('vendor_instructions', '')
        
        if courier_id == 'marketplace':
            return redirect('store:publish_to_marketplace', order_id=order.id)
        
        # Assigner livreur spécifique
        try:
            courier = get_object_or_404(DeliveryProfile, id=courier_id, is_available=True)
            
            distance_km = calculate_delivery_distance(order)
            commission_amount = calculate_commission(distance_km)
            
            assignment = DeliveryAssignment.objects.create(
                order=order,
                vendor=request.user,
                delivery_person=courier.user,
                commission_amount=commission_amount,
                commission_payer=order.commission_payer,
                distance_km=distance_km,
                vendor_instructions=vendor_instructions,
                expires_at=timezone.now() + timedelta(hours=24)
            )
            
            order.delivery_person = courier.user
            order.delivery_assigned_at = timezone.now()
            order.status = 'shipped'
            order.save()
            
            # Notification livreur
            Notification.objects.create(
                user=courier.user,
                notification_type='delivery_assigned',
                message=f"Nouvelle livraison assignée: Commande #{order.id}",
                related_object_id=order.id
            )
            
            messages.success(request, f"Livraison assignée à {courier.user.username}")
            return redirect('store:vendor_pending_orders')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de l'assignation: {str(e)}")
    
    # Livreurs disponibles
    available_couriers = DeliveryProfile.objects.filter(
        is_available=True,
        user__is_active=True
    ).select_related('user')
    
    context = {
        'order': order,
        'available_couriers': available_couriers,
    }
    return render(request, 'store/select_delivery_person.html', context)

@login_required
def publish_to_marketplace(request, order_id):
    """Publier sur le marketplace des livreurs"""
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier permissions
    if not (request.user.is_staff or 
            (request.user.user_type == 'seller' and 
             order.items.filter(product__seller=request.user).exists())):
        return HttpResponseForbidden("Accès non autorisé")
    
    if request.method == 'POST':
        commission_bonus = float(request.POST.get('commission_bonus', 0))
        vendor_instructions = request.POST.get('vendor_instructions', '')
        
        distance_km = calculate_delivery_distance(order)
        base_commission = calculate_commission(distance_km)
        total_commission = base_commission + commission_bonus
        
        assignment = DeliveryAssignment.objects.create(
            order=order,
            vendor=request.user,
            commission_amount=total_commission,
            commission_payer=order.commission_payer,
            distance_km=distance_km,
            vendor_instructions=vendor_instructions,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        order.status = 'processing'
        order.save()
        
        messages.success(request, "Course publiée sur le marketplace!")
        return redirect('store:vendor_pending_orders')
    
    distance_km = calculate_delivery_distance(order)
    base_commission = calculate_commission(distance_km)
    
    context = {
        'order': order,
        'distance_km': distance_km,
        'base_commission': base_commission,
    }
    return render(request, 'store/publish_marketplace.html', context)

# === VUES LIVREUR ===

@login_required
def delivery_marketplace(request):
    """Marketplace des livraisons pour livreurs"""
    if request.user.user_type != 'delivery':
        return HttpResponseForbidden("Accès réservé aux livreurs")
    
    # Assignations disponibles
    available_assignments = DeliveryAssignment.objects.filter(
        status='pending',
        delivery_person__isnull=True,
        expires_at__gt=timezone.now()
    ).select_related('order', 'vendor').order_by('-commission_amount')
    
    # Mes assignations
    my_assignments = DeliveryAssignment.objects.filter(
        delivery_person=request.user,
        status__in=['accepted', 'picked_up', 'in_transit']
    ).select_related('order', 'vendor').order_by('-accepted_at')
    
    context = {
        'available_assignments': available_assignments,
        'my_assignments': my_assignments,
    }
    return render(request, 'store/delivery_marketplace.html', context)

@login_required
def accept_delivery_assignment(request, assignment_id):
    """Accepter une assignation de livraison"""
    if request.user.user_type != 'delivery':
        return HttpResponseForbidden("Accès réservé aux livreurs")
    
    assignment = get_object_or_404(DeliveryAssignment, id=assignment_id, status='pending')
    
    if assignment.is_expired:
        messages.error(request, "Cette assignation a expiré.")
        return redirect('store:delivery_marketplace')
    
    try:
        with transaction.atomic():
            assignment.accept_delivery(request.user)
            
            order = assignment.order
            order.delivery_person = request.user
            order.delivery_assigned_at = timezone.now()
            order.status = 'shipped'
            order.save()
            
            # Notification vendeur
            Notification.objects.create(
                user=assignment.vendor,
                notification_type='delivery_accepted',
                message=f"Livraison acceptée par {request.user.username} pour commande #{order.id}",
                related_object_id=order.id
            )
            
            messages.success(request, f"Livraison acceptée! Commande #{order.id}")
            return redirect('store:delivery_marketplace')
            
    except Exception as e:
        messages.error(request, f"Erreur: {str(e)}")
        return redirect('store:delivery_marketplace')

@login_required
def delivery_dashboard(request):
    """Tableau de bord livreur"""
    if request.user.user_type != 'delivery':
        return HttpResponseForbidden("Accès réservé aux livreurs")
    
    try:
        delivery_profile = request.user.delivery_profile
    except:
        # Créer profil si inexistant
        delivery_profile = DeliveryProfile.objects.create(
            user=request.user,
            phone_number='',
            vehicle_type='bike'
        )
    
    # Statistiques
    total_deliveries = delivery_profile.total_deliveries
    today_deliveries = DeliveryAssignment.objects.filter(
        delivery_person=request.user,
        status='delivered',
        delivered_at__date=timezone.now().date()
    ).count()
    
    pending_deliveries = DeliveryAssignment.objects.filter(
        delivery_person=request.user,
        status__in=['accepted', 'picked_up', 'in_transit']
    ).count()
    
    available_orders = DeliveryAssignment.objects.filter(
        status='pending',
        delivery_person__isnull=True,
        expires_at__gt=timezone.now()
    ).count()
    
    context = {
        'delivery_profile': delivery_profile,
        'total_deliveries': total_deliveries,
        'today_deliveries': today_deliveries,
        'pending_deliveries': pending_deliveries,
        'available_orders': available_orders,
    }
    return render(request, 'store/delivery_dashboard.html', context)

@login_required
def delivery_profile_management(request):
    """Gestion du profil livreur"""
    if request.user.user_type != 'delivery':
        return HttpResponseForbidden("Accès réservé aux livreurs")
    
    try:
        profile = request.user.delivery_profile
    except:
        profile = DeliveryProfile.objects.create(
            user=request.user,
            phone_number='',
            vehicle_type='bike'
        )
    
    if request.method == 'POST':
        # Mise à jour disponibilité
        if 'is_available' in request.POST:
            profile.is_available = request.POST.get('is_available') == 'on'
            profile.save()
            status = "disponible" if profile.is_available else "indisponible"
            messages.success(request, f"Statut mis à jour: {status}")
            return redirect('store:delivery_profile_management')
        
        # Mise à jour profil
        profile.phone_number = request.POST.get('phone_number', '')
        profile.vehicle_type = request.POST.get('vehicle_type', 'bike')
        profile.license_number = request.POST.get('license_number', '')
        profile.save()
        
        messages.success(request, "Profil mis à jour avec succès.")
        return redirect('store:delivery_profile_management')
    
    # Statistiques
    total_earnings = DeliveryAssignment.objects.filter(
        delivery_person=request.user,
        status='delivered'
    ).aggregate(total=Sum('commission_amount'))['total'] or 0
    
    pending_assignments = DeliveryAssignment.objects.filter(
        delivery_person=request.user,
        status__in=['accepted', 'picked_up', 'in_transit']
    ).count()
    
    context = {
        'profile': profile,
        'total_earnings': total_earnings,
        'pending_assignments': pending_assignments,
    }
    return render(request, 'store/delivery_profile.html', context)

# === VUES PRODUITS VENDEUR ===

@login_required
def product_create(request):
    """Créer un produit (vendeur)"""
    if request.user.user_type != 'seller':
        messages.error(request, "Seuls les vendeurs peuvent créer des produits.")
        return redirect('store:home')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            
            # Créer modération
            from admin_panel.models import ProductModeration
            ProductModeration.objects.create(
                product=product,
                status='pending',
                reason='Nouveau produit en attente d\'approbation'
            )
            
            messages.success(request, "Produit créé et soumis pour approbation.")
            return redirect('store:product_detail', product_id=product.id)
    else:
        form = ProductForm()
    
    return render(request, 'store/product_form.html', {'form': form})

@login_required
def product_update(request, pk):
    """Modifier un produit"""
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Produit mis à jour avec succès.")
            return redirect('store:product_detail', product_id=product.id)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'store/product_form.html', {'form': form, 'product': product})

@login_required
def product_delete(request, pk):
    """Supprimer un produit"""
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f"Produit '{product_name}' supprimé avec succès.")
        return redirect('store:product_list')
    
    return render(request, 'store/product_confirm_delete.html', {'product': product})

# === AUTRES VUES ===

def autocomplete_search(request):
    """Autocomplétion pour la recherche"""
    query = request.GET.get('q', '')
    suggestions = []
    
    if len(query) >= 2:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(brand__icontains=query),
            is_sold=False,
            sold_out=False,
            stock__gt=0
        )[:5]
        
        suggestions = [
            {
                'name': product.name,
                'brand': product.brand or 'Sans marque',
                'price': float(product.discounted_price),
            }
            for product in products
        ]
    
    return JsonResponse({'suggestions': suggestions})

def geocode(request):
    """Géocodage inverse"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})
    
    try:
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not latitude or not longitude:
            return JsonResponse({'status': 'error', 'message': 'Coordonnées manquantes'})
        
        # Utiliser Nominatim pour le géocodage inverse
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'addressdetails': 1
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            address_data = data.get('address', {})
            
            return JsonResponse({
                'status': 'success',
                'address': {
                    'street_address': address_data.get('road', ''),
                    'city': address_data.get('city', address_data.get('town', address_data.get('village', ''))),
                    'postal_code': address_data.get('postcode', ''),
                    'country': address_data.get('country', 'Guinée')
                }
            })
        else:
            return JsonResponse({'status': 'error', 'message': 'Erreur de géocodage'})
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# === VUES D'ERREUR ===

def custom_404(request, exception):
    """Page 404 personnalisée"""
    return render(request, '404.html', status=404)

def custom_500(request):
    """Page 500 personnalisée"""
    return render(request, '500.html', status=500)

# === VUES SELLER PROFILE ===

@login_required
def seller_profile(request):
    """Profil vendeur (modification)"""
    if request.user.user_type != 'seller':
        return HttpResponseForbidden("Accès réservé aux vendeurs")
    
    profile, created = SellerProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = SellerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil vendeur mis à jour avec succès.")
            return redirect('store:seller_profile')
    else:
        form = SellerProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    return render(request, 'accounts/seller_profile.html', context)

def seller_public_profile(request, username):
    """Profil public d'un vendeur"""
    seller = get_object_or_404(User, username=username, user_type='seller')
    profile, created = SellerProfile.objects.get_or_create(user=seller)
    
    # Produits du vendeur
    products = Product.objects.filter(
        seller=seller,
        is_sold=False,
        sold_out=False,
        stock__gt=0
    )[:12]
    
    # Notes du vendeur
    ratings = SellerRating.objects.filter(seller=seller).order_by('-created_at')[:10]
    
    # Calculer note moyenne
    avg_rating = ratings.aggregate(avg=Avg('rating'))['avg'] or 0
    profile.average_rating = round(avg_rating, 1)
    
    context = {
        'seller': seller,
        'profile': profile,
        'products': products,
        'ratings': ratings,
    }
    return render(request, 'accounts/seller_public_profile.html', context)

# === VUES MESSAGES ===

@login_required
def messages_view(request):
    """Liste des conversations"""
    conversations = Conversation.objects.filter(
        Q(initiator=request.user) | Q(recipient=request.user)
    ).order_by('-created_at')
    
    context = {
        'conversations': conversations,
    }
    return render(request, 'store/messages.html', context)

@login_required
def message_seller(request, product_id):
    """Envoyer un message au vendeur"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.user == product.seller:
        messages.error(request, "Vous ne pouvez pas vous envoyer un message.")
        return redirect('store:product_detail', product_id=product.id)
    
    # Créer ou récupérer conversation
    conversation, created = Conversation.objects.get_or_create(
        initiator=request.user,
        recipient=product.seller,
        product=product
    )
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=form.cleaned_data['content']
            )
            
            # Notification
            Notification.objects.create(
                user=product.seller,
                notification_type='new_message',
                message=f"Nouveau message de {request.user.username}",
                related_object_id=conversation.id
            )
            
            messages.success(request, "Message envoyé avec succès.")
            return redirect('chat:conversation', conversation_id=conversation.id)
    else:
        form = MessageForm()
    
    # Messages existants
    messages_list = conversation.messages.order_by('sent_at')
    other_user = product.seller
    
    context = {
        'form': form,
        'conversation': conversation,
        'messages': messages_list,
        'other_user': other_user,
        'product': product,
    }
    return render(request, 'store/messages.html', context)

# === VUES AVIS ===

@login_required
def reply_to_review(request, review_id):
    """Répondre à un avis (vendeur)"""
    review = get_object_or_404(Review, id=review_id, product__seller=request.user)
    
    if request.method == 'POST':
        form = ReviewReplyForm(request.POST)
        if form.is_valid():
            review.reply = form.cleaned_data['reply']
            review.save()
            
            # Notification client
            Notification.objects.create(
                user=review.user,
                notification_type='review_reply',
                message=f"Le vendeur a répondu à votre avis sur {review.product.name}",
                related_object_id=review.product.id
            )
            
            messages.success(request, "Réponse ajoutée avec succès.")
            return redirect('store:product_detail', product_id=review.product.id)
    else:
        form = ReviewReplyForm()
    
    context = {
        'form': form,
        'review': review,
    }
    return render(request, 'store/reply_to_review.html', context)

# === VUES DEMANDES PRODUITS ===

@login_required
def respond_product_request(request, request_id):
    """Répondre à une demande de produit"""
    product_request = get_object_or_404(ProductRequest, id=request_id, product__seller=request.user)
    
    if request.method == 'POST':
        form = ProductRequestResponseForm(request.POST)
        if form.is_valid():
            response_text = form.cleaned_data['response']
            restock_quantity = form.cleaned_data.get('restock_quantity', 0)
            
            # Mettre à jour le stock si nécessaire
            if restock_quantity > 0:
                product_request.product.stock += restock_quantity
                product_request.product.save()
            
            # Marquer comme traité
            product_request.is_notified = True
            product_request.save()
            
            # Notification client
            user_to_notify = product_request.user
            if user_to_notify:
                Notification.objects.create(
                    user=user_to_notify,
                    notification_type='product_available',
                    message=f"Réponse du vendeur pour {product_request.product.name}: {response_text}",
                    related_object_id=product_request.product.id
                )
            
            messages.success(request, "Réponse envoyée avec succès.")
            return redirect('dashboard:requests')
    else:
        form = ProductRequestResponseForm()
    
    context = {
        'form': form,
        'product_request': product_request,
    }
    return render(request, 'store/respond_product_request.html', context)

# === VUES NOTATION VENDEUR ===

@login_required
def rate_seller(request, order_id):
    """Noter les vendeurs d'une commande"""
    order = get_object_or_404(Order, id=order_id, user=request.user, status='delivered')
    
    # Récupérer tous les vendeurs de cette commande
    sellers = set()
    for item in order.items.all():
        if item.seller:
            sellers.add(item.seller)
    
    if request.method == 'POST':
        for seller in sellers:
            rating_key = f'rating_{seller.id}'
            comment_key = f'comment_{seller.id}'
            
            rating = request.POST.get(rating_key)
            comment = request.POST.get(comment_key, '')
            
            if rating:
                SellerRating.objects.get_or_create(
                    seller=seller,
                    rater=request.user,
                    order=order,
                    defaults={
                        'rating': int(rating),
                        'comment': comment
                    }
                )
        
        messages.success(request, "Notations enregistrées avec succès.")
        return redirect('store:order_history')
    
    context = {
        'order': order,
        'sellers': sellers,
    }
    return render(request, 'store/rate_seller.html', context)

# === VUES SIGNALEMENT ===

class ReportCreateView(LoginRequiredMixin, CreateView):
    """Créer un signalement"""
    model = Report
    form_class = ReportForm
    template_name = 'store/report_form.html'
    
    def form_valid(self, form):
        form.instance.reporter = self.request.user
        
        # Récupérer l'objet signalé
        product_id = self.request.GET.get('product_id')
        user_id = self.request.GET.get('user_id')
        
        if product_id:
            form.instance.product = get_object_or_404(Product, id=product_id)
        elif user_id:
            form.instance.user = get_object_or_404(User, id=user_id)
        
        messages.success(self.request, "Signalement envoyé avec succès.")
        return super().form_valid(form)
    
    def get_success_url(self):
        if self.object.product:
            return reverse('store:product_detail', kwargs={'product_id': self.object.product.id})
        return reverse('store:home')

# === VUES ABONNEMENTS ===

@login_required
def subscription_plans(request):
    """Plans d'abonnement"""
    try:
        subscription = request.user.subscription
    except:
        subscription = Subscription.objects.create(user=request.user, plan='free')
    
    context = {
        'subscription': subscription,
    }
    return render(request, 'store/subscription_plans.html', context)

@login_required
def create_subscription(request):
    """Créer/modifier abonnement"""
    if request.method == 'POST':
        plan = request.POST.get('plan', 'free')
        
        subscription, created = Subscription.objects.get_or_create(
            user=request.user,
            defaults={'plan': plan, 'active': True}
        )
        
        if not created:
            subscription.plan = plan
            subscription.active = True
            subscription.save()
        
        messages.success(request, f"Abonnement {plan} activé avec succès.")
        return redirect('store:subscription_plans')
    
    return redirect('store:subscription_plans')

# === VUES COMMANDES VENDEUR ===

@login_required
def seller_order_list(request):
    """Liste des commandes pour un vendeur"""
    if request.user.user_type != 'seller':
        return HttpResponseForbidden("Accès réservé aux vendeurs")
    
    # Récupérer les commandes contenant des produits du vendeur
    orders = Order.objects.filter(
        items__product__seller=request.user
    ).distinct().order_by('-created_at')
    
    # Enrichir avec les items du vendeur
    orders_with_items = []
    for order in orders:
        seller_items = order.items.filter(product__seller=request.user)
        total = sum(item.quantity * item.price for item in seller_items)
        orders_with_items.append({
            'order': order,
            'items': seller_items,
            'total': total
        })
    
    context = {
        'orders': orders_with_items,
    }
    return render(request, 'store/seller_order_list.html', context)

@login_required
def update_order_status(request, order_id):
    """Mettre à jour le statut d'une commande"""
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier permissions
    if not (request.user.is_staff or 
            (request.user.user_type == 'seller' and 
             order.items.filter(product__seller=request.user).exists())):
        return HttpResponseForbidden("Accès non autorisé")
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            
            # Notification client
            Notification.objects.create(
                user=order.user,
                notification_type='order_status_update',
                message=f"Statut de votre commande #{order.id} mis à jour: {order.get_status_display()}",
                related_object_id=order.id
            )
            
            messages.success(request, f"Statut mis à jour: {order.get_status_display()}")
        else:
            messages.error(request, "Statut invalide.")
    
    return redirect('store:seller_order_list')

@login_required
def mark_as_sold(request, product_id):
    """Marquer un produit comme vendu"""
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        product.is_sold = True
        product.stock = 0
        product.save()
        messages.success(request, f"Produit '{product.name}' marqué comme vendu.")
        return redirect('store:product_detail', product_id=product.id)
    
    return render(request, 'store/confirm_sold.html', {'product': product})

# === VUES RÉDUCTIONS ===

@login_required
def apply_discount_for_product(request, product_id):
    """Appliquer une réduction à un produit spécifique"""
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        form = DiscountForm(request.POST, user=request.user)
        if form.is_valid():
            from .models import Discount
            
            discount = Discount.objects.create(
                product=product,
                percentage=form.cleaned_data['percentage'],
                start_date=form.cleaned_data['start_date'],
                end_date=form.cleaned_data['end_date'],
                is_active=True
            )
            
            messages.success(request, f"Réduction de {discount.percentage}% appliquée à {product.name}")
            return redirect('store:product_detail', product_id=product.id)
    else:
        form = DiscountForm(user=request.user)
        # Pré-sélectionner le produit
        form.fields['products'].initial = [product]
    
    context = {
        'form': form,
        'product': product,
    }
    return render(request, 'store/apply_discount.html', context)

@login_required
def apply_discount_multiple(request):
    """Appliquer une réduction à plusieurs produits"""
    if request.user.user_type != 'seller':
        return HttpResponseForbidden("Accès réservé aux vendeurs")
    
    if request.method == 'POST':
        form = DiscountForm(request.POST, user=request.user)
        if form.is_valid():
            from .models import Discount
            
            products = form.cleaned_data['products']
            percentage = form.cleaned_data['percentage']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            for product in products:
                Discount.objects.create(
                    product=product,
                    percentage=percentage,
                    start_date=start_date,
                    end_date=end_date,
                    is_active=True
                )
            
            messages.success(request, f"Réduction de {percentage}% appliquée à {products.count()} produits")
            return redirect('dashboard:products')
    else:
        form = DiscountForm(user=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'store/apply_discount.html', context)