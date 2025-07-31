from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404, HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum
from django.views.generic import CreateView, UpdateView, DeleteView, View
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import json
from django.db import models
import stripe
import paypalrestsdk
import requests
import qrcode
import base64

User = get_user_model()
from io import BytesIO
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import timedelta

from .models import (
    Product, Category, Cart, CartItem, Order, OrderItem, Address, ShippingOption, Discount,
    Favorite, Review, Notification, ProductView, ProductRequest, Conversation, Message,
    SellerRating, SellerProfile, Subscription, QRDeliveryCode, DeliveryProfile, DeliveryRating,
    Conversation, Message, SellerRating, Subscription, Discount,
    QRDeliveryCode, DeliveryAssignment, DeliveryProfile
)
from .forms import ProductForm, AddressForm, ReviewForm, CartItemForm, ProductRequestForm, ReportForm, CheckoutForm
from marketing.models import PromoCode, LoyaltyPoint
from admin_panel.models import Report


# === Vues de géolocalisation ===
@login_required

User = get_user_model()

def geocode(request):
    """Géocodage inverse pour obtenir une adresse à partir de coordonnées"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            if not latitude or not longitude:
                return JsonResponse({'status': 'error', 'message': 'Coordonnées manquantes'})
            
            # Utiliser Nominatim pour le géocodage inverse
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=18&addressdetails=1"
            
            response = requests.get(url, headers={'User-Agent': 'LuxeShop/1.0'})
            
            if response.status_code == 200:
                data = response.json()
                address_data = data.get('address', {})
                
                formatted_address = {
                    'street_address': address_data.get('road', ''),
                    'city': address_data.get('city', address_data.get('town', address_data.get('village', ''))),
                    'postal_code': address_data.get('postcode', ''),
                    'country': address_data.get('country', 'Guinée')
                }
                
                return JsonResponse({
                    'status': 'success',
                    'address': formatted_address
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Service de géocodage indisponible'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})

# === Vues vendeur ===
@login_required
def seller_order_list(request):
    """Liste des commandes pour un vendeur"""
    if request.user.user_type != 'seller':
        messages.error(request, "Accès réservé aux vendeurs.")
        return redirect('store:home')
    
    # Récupérer les commandes où l'utilisateur est vendeur
    orders = Order.objects.filter(
        items__product__seller=request.user
    ).distinct().order_by('-created_at')
    
    # Ajouter les informations des articles pour chaque commande
    orders_with_items = []
    for order in orders:
        items = order.items.filter(product__seller=request.user)
        total = sum(item.quantity * item.price for item in items)
        orders_with_items.append({
            'order': order,
            'items': items,
            'total': total
        })
    
    return render(request, 'store/seller_order_list.html', {
        'orders': orders_with_items
    })

@login_required
def update_order_status(request, order_id):
    """Mettre à jour le statut d'une commande"""
    if request.user.user_type != 'seller':
        messages.error(request, "Accès réservé aux vendeurs.")
        return redirect('store:home')
    
    order = get_object_or_404(Order, id=order_id, items__product__seller=request.user)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            
            # Notifier l'acheteur
            Notification.objects.create(
                user=order.user,
                notification_type='order_status_updated',
                message=f"Le statut de votre commande #{order.id} a été mis à jour: {order.get_status_display()}",
                related_object_id=order.id
            )
            
            messages.success(request, f"Statut de la commande #{order.id} mis à jour.")
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
        messages.success(request, f"Le produit '{product.name}' a été marqué comme vendu.")
        return redirect('store:product_detail', product_id=product.id)
    
    return render(request, 'store/confirm_sold.html', {'product': product})

@login_required
def apply_discount_for_product(request, product_id):
    """Appliquer une réduction à un produit spécifique"""
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        percentage = request.POST.get('percentage')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        try:
            percentage = Decimal(percentage)
            if 0 < percentage <= 100:
                Discount.objects.create(
                    product=product,
                    percentage=percentage,
                    start_date=start_date,
                    end_date=end_date,
                    is_active=True
                )
                messages.success(request, f"Réduction de {percentage}% appliquée au produit.")
            else:
                messages.error(request, "Le pourcentage doit être entre 1 et 100.")
        except (ValueError, TypeError):
            messages.error(request, "Pourcentage invalide.")
        
        return redirect('store:product_detail', product_id=product.id)
    
    return render(request, 'store/apply_discount.html', {'product': product})

@login_required
def apply_discount_multiple(request):
    """Appliquer une réduction à plusieurs produits"""
    if request.user.user_type != 'seller':
        messages.error(request, "Accès réservé aux vendeurs.")
        return redirect('store:home')
    
    products = Product.objects.filter(seller=request.user, is_sold=False)
    
    if request.method == 'POST':
        selected_products = request.POST.getlist('products')
        percentage = request.POST.get('percentage')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        try:
            percentage = Decimal(percentage)
            if 0 < percentage <= 100 and selected_products:
                for product_id in selected_products:
                    product = Product.objects.get(id=product_id, seller=request.user)
                    Discount.objects.create(
                        product=product,
                        percentage=percentage,
                        start_date=start_date,
                        end_date=end_date,
                        is_active=True
                    )
                messages.success(request, f"Réduction appliquée à {len(selected_products)} produit(s).")
            else:
                messages.error(request, "Données invalides.")
        except (ValueError, TypeError, Product.DoesNotExist):
            messages.error(request, "Erreur lors de l'application de la réduction.")
        
        return redirect('dashboard:products')
    
    return render(request, 'store/apply_discount.html', {'products': products})

# === Vues de messagerie ===
@login_required
def messages_view(request):
    """Afficher les conversations de l'utilisateur"""
    conversations = Conversation.objects.filter(
        Q(initiator=request.user) | Q(recipient=request.user)
    ).order_by('-created_at')
    
    return render(request, 'store/messages.html', {
        'conversations': conversations
    })

@login_required
def message_seller(request, product_id):
    """Envoyer un message au vendeur d'un produit"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.user == product.seller:
        messages.error(request, "Vous ne pouvez pas vous envoyer un message.")
        return redirect('store:product_detail', product_id=product.id)
    
    # Créer ou récupérer la conversation
    conversation, created = Conversation.objects.get_or_create(
        initiator=request.user,
        recipient=product.seller,
        product=product
    )
    
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content
            )
            
            # Notifier le vendeur
            Notification.objects.create(
                user=product.seller,
                notification_type='new_message',
                message=f"Nouveau message de {request.user.username} concernant {product.name}",
                related_object_id=conversation.id
            )
            
            messages.success(request, "Message envoyé avec succès.")
            return redirect('chat:conversation', conversation_id=conversation.id)
    
    return render(request, 'store/messages.html', {
        'conversation': conversation,
        'product': product
    })

# === Vues des avis ===
@login_required
def reply_to_review(request, review_id):
    """Répondre à un avis"""
    review = get_object_or_404(Review, id=review_id, product__seller=request.user)
    
    if request.method == 'POST':
        reply = request.POST.get('reply')
        if reply:
            review.reply = reply
            review.save()
            
            # Notifier l'auteur de l'avis
            Notification.objects.create(
                user=review.user,
                notification_type='review_reply',
                message=f"Le vendeur a répondu à votre avis sur {review.product.name}",
                related_object_id=review.product.id
            )
            
            messages.success(request, "Réponse ajoutée avec succès.")
        else:
            messages.error(request, "Veuillez saisir une réponse.")
        
        return redirect('store:product_detail', product_id=review.product.id)
    
    return render(request, 'store/reply_to_review.html', {'review': review})

# === Vues des demandes de produits ===
@login_required
def respond_product_request(request, request_id):
    """Répondre à une demande de produit"""
    product_request = get_object_or_404(ProductRequest, id=request_id, product__seller=request.user)
    
    if request.method == 'POST':
        response = request.POST.get('response')
        restock_quantity = request.POST.get('restock_quantity')
        
        if response:
            # Envoyer la réponse par notification
            Notification.objects.create(
                user=product_request.user,
                notification_type='product_request_response',
                message=f"Réponse à votre demande pour {product_request.product.name}: {response}",
                related_object_id=product_request.product.id
            )
            
            # Restockage si spécifié
            if restock_quantity:
                try:
                    quantity = int(restock_quantity)
                    if quantity > 0:
                        product_request.product.stock += quantity
                        product_request.product.sold_out = False
                        product_request.product.save()
                        messages.success(request, f"Stock mis à jour (+{quantity} unités).")
                except ValueError:
                    messages.error(request, "Quantité invalide.")
            
            product_request.is_notified = True
            product_request.save()
            
            messages.success(request, "Réponse envoyée avec succès.")
        else:
            messages.error(request, "Veuillez saisir une réponse.")
        
        return redirect('dashboard:requests')
    
    return render(request, 'store/respond_product_request.html', {
        'product_request': product_request
    })

# === Vues de notation des vendeurs ===
@login_required
def rate_seller(request, order_id):
    """Noter les vendeurs d'une commande"""
    order = get_object_or_404(Order, id=order_id, user=request.user, status='delivered')
    
    # Récupérer tous les vendeurs de cette commande
    sellers = set(item.product.seller for item in order.items.all() if item.product.seller)
    
    if request.method == 'POST':
        for seller in sellers:
            rating_value = request.POST.get(f'rating_{seller.id}')
            comment = request.POST.get(f'comment_{seller.id}', '')
            
            if rating_value:
                SellerRating.objects.get_or_create(
                    seller=seller,
                    rater=request.user,
                    order=order,
                    defaults={
                        'rating': int(rating_value),
                        'comment': comment
                    }
                )
        
        messages.success(request, "Notations enregistrées avec succès.")
        return redirect('store:order_history')
    
    return render(request, 'store/rate_seller.html', {
        'order': order,
        'sellers': sellers
    })

# === Vue profil vendeur ===
@login_required
def seller_profile(request):
    """Modifier le profil vendeur"""
    if request.user.user_type != 'seller':
        messages.error(request, "Accès réservé aux vendeurs.")
        return redirect('store:home')
    
    profile, created = SellerProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Mise à jour des champs du profil
        profile.first_name = request.POST.get('first_name', '')
        profile.last_name = request.POST.get('last_name', '')
        profile.description = request.POST.get('description', '')
        profile.business_name = request.POST.get('business_name', '')
        profile.business_address = request.POST.get('business_address', '')
        profile.contact_phone = request.POST.get('contact_phone', '')
        
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
        
        profile.save()
        messages.success(request, "Profil mis à jour avec succès.")
        return redirect('store:seller_profile')
    
    return render(request, 'accounts/seller_profile.html', {
        'form': profile  # Passer l'objet profile comme form pour compatibilité template
    })

@login_required
def view_qr_code(request, order_id):
    """Affiche le QR Code d'une commande pour le vendeur"""
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier que l'utilisateur est le vendeur de cette commande
    if not order.items.filter(product__seller=request.user).exists():
        return HttpResponseForbidden("Vous n'êtes pas autorisé à voir ce QR Code.")
    
    try:
        qr_code = order.qr_code
        
        # Générer l'image QR Code
        qr_url = f"{settings.SITE_URL}{qr_code.qr_url}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        # Créer l'image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir en base64 pour l'affichage
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        context = {
            'order': order,
            'qr_code': qr_code,
            'qr_image': img_str,
            'qr_url': qr_url
        }
        
        return render(request, 'store/qr_code_view.html', context)
        
    except QRDeliveryCode.DoesNotExist:
        messages.error(request, "QR Code non trouvé pour cette commande.")
        return redirect('dashboard:orders')

def scan_qr_payment(request, code):
    """Page de paiement accessible via scan QR Code"""
    try:
        qr_code = get_object_or_404(QRDeliveryCode, code=code)
        
        # Vérifier que le QR Code n'a pas expiré
        if qr_code.is_expired:
            return render(request, 'store/qr_expired.html', {'qr_code': qr_code})
        
        # Vérifier que la commande n'est pas déjà payée
        if qr_code.order.status == 'delivered':
            return render(request, 'store/already_paid.html', {'order': qr_code.order})
        
        order = qr_code.order
        
        context = {
            'order': order,
            'qr_code': qr_code,
            'delivery_info': {
                'address': qr_code.delivery_address,
                'mode': qr_code.get_delivery_mode_display(),
                'payment_method': qr_code.get_preferred_payment_method_display(),
                'instructions': qr_code.special_instructions
            }
        }
        
        return render(request, 'store/qr_payment.html', context)
        
    except QRDeliveryCode.DoesNotExist:
        return render(request, 'store/qr_not_found.html')

@login_required
def vendor_pending_orders(request):
    """Liste des commandes en attente pour le vendeur"""
    if request.user.user_type != 'seller':
        return HttpResponseForbidden("Accès réservé aux vendeurs.")
    
    # Commandes en attente du vendeur
    pending_orders = Order.objects.filter(
        items__product__seller=request.user,
        status='pending'
    ).distinct().order_by('-created_at')
    
    context = {
        'pending_orders': pending_orders
    }
    
    return render(request, 'store/vendor_pending_orders.html', context)

@login_required
def assign_delivery_choice(request, order_id):
    """Interface vendeur pour choisir le mode de livraison"""
    if request.user.user_type != 'seller':
        messages.error(request, "Accès réservé aux vendeurs.")
        return redirect('store:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier que c'est bien une commande du vendeur
    if not order.items.filter(product__seller=request.user).exists():
        messages.error(request, "Cette commande ne vous appartient pas.")
        return redirect('store:vendor_pending_orders')
    
    # Vérifier que la commande n'est pas déjà assignée
    if hasattr(order, 'delivery_assignment'):
        messages.info(request, "Cette commande a déjà été assignée.")
        return redirect('store:vendor_pending_orders')
    
    if request.method == 'POST':
        delivery_choice = request.POST.get('delivery_choice')
        
        if delivery_choice == 'self':
            # Vendeur livre lui-même
            order.status = 'processing'
            order.save()
            
            # Créer l'assignation avec le vendeur comme livreur
            DeliveryAssignment.objects.create(
                order=order,
                vendor=request.user,
                delivery_person=request.user,  # Vendeur livre lui-même
                commission_amount=0,  # Pas de commission si vendeur livre
                commission_payer='vendor',
                distance_km=0,
                status='accepted',
                assigned_at=timezone.now(),
                accepted_at=timezone.now(),
                expires_at=timezone.now() + timedelta(hours=24),
                vendor_instructions="Livraison par le vendeur"
            )
            
            # Notification client
            Notification.objects.create(
                user=order.user,
                message=f"Votre commande #{order.id} sera livrée directement par le vendeur.",
                notification_type='delivery_assigned',
                related_object_id=order.id
            )
            
            messages.success(request, f"Vous avez choisi de livrer la commande #{order.id} vous-même.")
            return redirect('store:vendor_pending_orders')
            
        elif delivery_choice == 'courier':
            # Assigner à un livreur
            return redirect('store:select_delivery_person', order_id=order.id)
    
    # Calculer la distance approximative pour estimer la commission
    distance_km = 5  # Distance par défaut, à calculer selon l'adresse
    commission = distance_km * 2  # 2€ par km
    
    available_couriers = User.objects.filter(
        user_type='delivery',
        delivery_profile__is_available=True
    ).count()
    
    return render(request, 'store/delivery_choice.html', {
        'order': order,
        'distance_km': distance_km,
        'commission': commission,
        'available_couriers': available_couriers
    })

@login_required
def select_delivery_person(request, order_id):
    """Sélection d'un livreur spécifique"""
    if request.user.user_type != 'seller':
        messages.error(request, "Accès réservé aux vendeurs.")
        return redirect('store:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier que c'est bien une commande du vendeur
    if not order.items.filter(product__seller=request.user).exists():
        messages.error(request, "Cette commande ne vous appartient pas.")
        return redirect('store:vendor_pending_orders')
    
    # Livreurs disponibles
    available_couriers = User.objects.filter(
        user_type='delivery',
        delivery_profile__is_available=True
    ).select_related('delivery_profile')
    
    if request.method == 'POST':
        courier_id = request.POST.get('courier_id')
        vendor_instructions = request.POST.get('vendor_instructions', '')
        
        if courier_id == 'marketplace':
            # Publier sur le marketplace pour tous les livreurs
            return redirect('store:publish_to_marketplace', order_id=order.id)
        
        if courier_id:
            courier = get_object_or_404(User, id=courier_id, user_type='delivery')
            
            # Calculer la distance et commission
            distance_km = 5  # À calculer selon l'adresse réelle
            commission_amount = distance_km * 2  # 2€ par km
            commission_payer = order.commission_payer
            
            # Créer l'assignation
            assignment = DeliveryAssignment.objects.create(
                order=order,
                vendor=request.user,
                delivery_person=courier,
                commission_amount=commission_amount,
                commission_payer=commission_payer,
                distance_km=distance_km,
                status='pending',
                assigned_at=timezone.now(),
                expires_at=timezone.now() + timedelta(hours=24),
                vendor_instructions=vendor_instructions
            )
            
            # Notification au livreur
            Notification.objects.create(
                user=courier,
                message=f"Nouvelle course disponible ! Commande #{order.id} - {commission_amount}€ de commission",
                notification_type='delivery_request',
                related_object_id=assignment.id
            )
            
            # Notification WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'notifications_{courier.id}',
                {
                    'type': 'new_notification',
                    'message': f"Nouvelle course #{order.id} - {commission_amount}€",
                    'notification_type': 'delivery_request',
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            messages.success(request, f"Course assignée à {courier.username}. Il a 24h pour accepter.")
            return redirect('store:vendor_pending_orders')
    
    return render(request, 'store/select_delivery_person.html', {
        'order': order,
        'available_couriers': available_couriers
    })

@login_required
def publish_to_marketplace(request, order_id):
    """Publier la course sur le marketplace pour tous les livreurs"""
    if request.user.user_type != 'seller':
        messages.error(request, "Accès réservé aux vendeurs.")
        return redirect('store:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier que c'est bien une commande du vendeur
    if not order.items.filter(product__seller=request.user).exists():
        messages.error(request, "Cette commande ne vous appartient pas.")
        return redirect('store:vendor_pending_orders')
    
    if request.method == 'POST':
        vendor_instructions = request.POST.get('vendor_instructions', '')
        commission_bonus = float(request.POST.get('commission_bonus', 0))
        
        # Calculer la distance et commission
        distance_km = 5  # À calculer selon l'adresse réelle
        base_commission = distance_km * 2  # 2€ par km
        total_commission = base_commission + commission_bonus
        
        # Créer l'assignation marketplace
        assignment = DeliveryAssignment.objects.create(
            order=order,
            vendor=request.user,
            delivery_person=None,  # Pas encore assigné
            commission_amount=total_commission,
            commission_payer=order.commission_payer,
            distance_km=distance_km,
            status='pending',
            assigned_at=timezone.now(),
            expires_at=timezone.now() + timedelta(hours=24),
            vendor_instructions=vendor_instructions
        )
        
        # Notifier tous les livreurs disponibles
        available_couriers = User.objects.filter(
            user_type='delivery',
            delivery_profile__is_available=True
        )
        
        for courier in available_couriers:
            Notification.objects.create(
                user=courier,
                message=f"Nouvelle course disponible ! #{order.id} - {total_commission}€ commission",
                notification_type='marketplace_delivery',
                related_object_id=assignment.id
            )
        
        messages.success(request, f"Course publiée sur le marketplace avec {total_commission}€ de commission.")
        return redirect('store:vendor_pending_orders')
    
    # Calculer commission de base
    distance_km = 5
    base_commission = distance_km * 2
    
    return render(request, 'store/publish_marketplace.html', {
        'order': order,
        'distance_km': distance_km,
        'base_commission': base_commission
    })

@login_required
def delivery_marketplace(request):
    """Marketplace des courses pour les livreurs"""
    if request.user.user_type != 'delivery':
        messages.error(request, "Accès réservé aux livreurs.")
        return redirect('store:home')
    
    # Courses disponibles (non assignées ou assignées mais pas acceptées)
    available_assignments = DeliveryAssignment.objects.filter(
        status='pending',
        expires_at__gt=timezone.now()
    ).select_related('order', 'vendor').order_by('-commission_amount')
    
    # Mes courses acceptées
    my_assignments = DeliveryAssignment.objects.filter(
        delivery_person=request.user,
        status__in=['accepted', 'picked_up', 'in_transit']
    ).select_related('order', 'vendor').order_by('-accepted_at')
    
    return render(request, 'store/delivery_marketplace.html', {
        'available_assignments': available_assignments,
        'my_assignments': my_assignments
    })

@login_required
def accept_delivery_assignment(request, assignment_id):
    """Accepter une assignation de livraison"""
    if request.user.user_type != 'delivery':
        messages.error(request, "Accès réservé aux livreurs.")
        return redirect('store:home')
    
    assignment = get_object_or_404(DeliveryAssignment, id=assignment_id)
    
    # Vérifier que l'assignation est encore disponible
    if assignment.status != 'pending':
        messages.error(request, "Cette course n'est plus disponible.")
        return redirect('store:delivery_marketplace')
    
    if assignment.is_expired:
        messages.error(request, "Cette course a expiré.")
        return redirect('store:delivery_marketplace')
    
    # Vérifier que le livreur est disponible
    if not request.user.delivery_profile.is_available:
        messages.error(request, "Vous devez être disponible pour accepter une course.")
        return redirect('store:delivery_marketplace')
    
    # Accepter l'assignation
    assignment.delivery_person = request.user
    assignment.status = 'accepted'
    assignment.accepted_at = timezone.now()
    assignment.save()
    
    # Mettre à jour le statut de la commande
    assignment.order.status = 'processing'
    assignment.order.save()
    
    # Marquer le livreur comme occupé
    request.user.delivery_profile.is_available = False
    request.user.delivery_profile.save()
    
    # Notifications
    # Au vendeur
    Notification.objects.create(
        user=assignment.vendor,
        message=f"Votre commande #{assignment.order.id} a été acceptée par {request.user.username}",
        notification_type='delivery_accepted',
        related_object_id=assignment.id
    )
    
    # Au client
    Notification.objects.create(
        user=assignment.order.user,
        message=f"Un livreur a accepté votre commande #{assignment.order.id}. Livraison en cours de préparation.",
        notification_type='delivery_accepted',
        related_object_id=assignment.order.id
    )
    
    messages.success(request, f"Course acceptée ! Rendez-vous chez {assignment.vendor.username} pour récupérer la commande.")
    return redirect('store:delivery_marketplace')

@login_required
def reject_delivery_assignment(request, assignment_id):
    """Rejeter une assignation de livraison"""
    if request.user.user_type != 'delivery':
        messages.error(request, "Accès réservé aux livreurs.")
        return redirect('store:home')
    
    assignment = get_object_or_404(DeliveryAssignment, id=assignment_id)
    
    if assignment.delivery_person != request.user:
        messages.error(request, "Cette assignation ne vous concerne pas.")
        return redirect('store:delivery_marketplace')
    
    # Rejeter l'assignation
    assignment.delivery_person = None
    assignment.status = 'pending'
    assignment.accepted_at = None
    assignment.save()
    
    # Notification au vendeur
    Notification.objects.create(
        user=assignment.vendor,
        message=f"Le livreur a refusé la commande #{assignment.order.id}. Choisissez un autre livreur.",
        notification_type='delivery_rejected',
        related_object_id=assignment.id
    )
    
    messages.info(request, "Course refusée.")
    return redirect('store:delivery_marketplace')

@login_required
def mark_picked_up(request, assignment_id):
    """Marquer comme récupéré chez le vendeur"""
    if request.user.user_type != 'delivery':
        messages.error(request, "Accès réservé aux livreurs.")
        return redirect('store:home')
    
    assignment = get_object_or_404(DeliveryAssignment, id=assignment_id, delivery_person=request.user)
    
    if assignment.status != 'accepted':
        messages.error(request, "Cette course n'est pas dans le bon statut.")
        return redirect('store:delivery_marketplace')
    
    # Marquer comme récupéré
    assignment.status = 'picked_up'
    assignment.picked_up_at = timezone.now()
    assignment.save()
    
    # Mettre à jour le statut de la commande
    assignment.order.status = 'shipped'
    assignment.order.save()
    
    # Notifications
    Notification.objects.create(
        user=assignment.order.user,
        message=f"Votre commande #{assignment.order.id} a été récupérée et est en route !",
        notification_type='order_shipped',
        related_object_id=assignment.order.id
    )
    
    Notification.objects.create(
        user=assignment.vendor,
        message=f"Commande #{assignment.order.id} récupérée par le livreur.",
        notification_type='order_picked_up',
        related_object_id=assignment.order.id
    )
    
    messages.success(request, "Commande récupérée ! Direction chez le client.")
    return redirect('store:delivery_marketplace')

@login_required
def complete_delivery_assignment(request, assignment_id):
    """Marquer la livraison comme terminée"""
    if request.user.user_type != 'delivery':
        messages.error(request, "Accès réservé aux livreurs.")
        return redirect('store:home')
    
    assignment = get_object_or_404(DeliveryAssignment, id=assignment_id, delivery_person=request.user)
    
    if assignment.status != 'picked_up':
        messages.error(request, "Vous devez d'abord récupérer la commande chez le vendeur.")
        return redirect('store:delivery_marketplace')
    
    # Marquer comme livré
    assignment.status = 'delivered'
    assignment.delivered_at = timezone.now()
    assignment.save()
    
    # Mettre à jour le statut de la commande
    assignment.order.status = 'delivered'
    assignment.order.save()
    
    # Marquer le livreur comme disponible
    request.user.delivery_profile.is_available = True
    request.user.delivery_profile.total_deliveries += 1
    request.user.delivery_profile.save()
    
    # Notifications
    Notification.objects.create(
        user=assignment.order.user,
        message=f"Votre commande #{assignment.order.id} a été livrée avec succès !",
        notification_type='order_delivered',
        related_object_id=assignment.order.id
    )
    
    Notification.objects.create(
        user=assignment.vendor,
        message=f"Commande #{assignment.order.id} livrée avec succès par {request.user.username}.",
        notification_type='delivery_completed',
        related_object_id=assignment.order.id
    )
    
    messages.success(request, f"Livraison terminée ! Commission de {assignment.commission_amount}€ ajoutée à vos gains.")
    return redirect('store:delivery_marketplace')

@login_required
def delivery_profile_management(request):
    """Gestion du profil livreur"""
    if request.user.user_type != 'delivery':
        messages.error(request, "Accès réservé aux livreurs.")
        return redirect('store:home')
    
    profile, created = DeliveryProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Mise à jour du statut de disponibilité
        is_available = request.POST.get('is_available') == 'on'
        profile.is_available = is_available
        
        # Mise à jour des autres champs
        profile.phone_number = request.POST.get('phone_number', profile.phone_number)
        profile.vehicle_type = request.POST.get('vehicle_type', profile.vehicle_type)
        profile.license_number = request.POST.get('license_number', profile.license_number)
        
        profile.save()
        
        status_text = "disponible" if is_available else "indisponible"
        messages.success(request, f"Profil mis à jour. Vous êtes maintenant {status_text}.")
        return redirect('store:delivery_profile_management')
    
    # Statistiques du livreur
    total_earnings = DeliveryAssignment.objects.filter(
        delivery_person=request.user,
        status='delivered'
    ).aggregate(total=models.Sum('commission_amount'))['total'] or 0
    
    pending_assignments = DeliveryAssignment.objects.filter(
        delivery_person=request.user,
        status__in=['accepted', 'picked_up']
    ).count()
    
    return render(request, 'store/delivery_profile.html', {
        'profile': profile,
        'total_earnings': total_earnings,
        'pending_assignments': pending_assignments
    })

@login_required
def cancel_delivery_assignment(request, order_id):
    """Annuler une assignation et remettre en marketplace"""
    if request.user.user_type != 'seller':
        messages.error(request, "Accès réservé aux vendeurs.")
        return redirect('store:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    try:
        assignment = DeliveryAssignment.objects.get(order=order, vendor=request.user)
    except DeliveryAssignment.DoesNotExist:
        messages.error(request, "Aucune assignation trouvée pour cette commande.")
        return redirect('store:vendor_pending_orders')
    
    if assignment.status == 'delivered':
        messages.error(request, "Impossible d'annuler une livraison terminée.")
        return redirect('store:vendor_pending_orders')
    
    # Si un livreur était assigné, le libérer
    if assignment.delivery_person:
        assignment.delivery_person.delivery_profile.is_available = True
        assignment.delivery_person.delivery_profile.save()
        
        # Notification au livreur
        Notification.objects.create(
            user=assignment.delivery_person,
            message=f"La course #{order.id} a été annulée par le vendeur.",
            notification_type='delivery_cancelled',
            related_object_id=assignment.id
        )
    
    order.status = 'pending'
    order.save()
    
def home(request):
    """Page d'accueil"""
    featured_products = Product.objects.filter(is_sold=False, sold_out=False, stock__gt=0)[:8]
    categories = Category.objects.all()[:6]
    return render(request, 'home.html', {
        'featured_products': featured_products,
        'categories': categories
    })

def product_list(request):
    """Liste des produits avec filtres"""
    products = Product.objects.filter(is_sold=False, sold_out=False, stock__gt=0)
    categories = Category.objects.all()
    
    # Filtres
    query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    size_filter = request.GET.get('size', '')
    brand_filter = request.GET.get('brand', '')
    color_filter = request.GET.get('color', '')
    material_filter = request.GET.get('material', '')
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(brand__icontains=query)
        )
    
    if category_filter:
        products = products.filter(category__name=category_filter)
    
    if price_min:
        try:
            products = products.filter(price__gte=Decimal(price_min))
        except:
            pass
    
    if price_max:
        try:
            products = products.filter(price__lte=Decimal(price_max))
        except:
            pass
    
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
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'selected_category': category_filter,
        'price_min': price_min,
        'price_max': price_max,
        'size_filter': size_filter,
        'brand_filter': brand_filter,
        'color_filter': color_filter,
        'material_filter': material_filter,
        'product_sizes': Product.SIZE_CHOICES,
    }
    
    return render(request, 'store/product_list.html', context)

def product_detail(request, product_id):
    """Détail d'un produit"""
    product = get_object_or_404(Product, id=product_id)
    
    # Incrémenter les vues
    product.views += 1
    product.save(update_fields=['views'])
    
    # Avis et moyenne
    reviews = product.reviews.filter(is_approved=True)
    average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Vérifier si l'utilisateur peut laisser un avis
    can_review = False
    has_reviewed = False
    if request.user.is_authenticated:
        has_reviewed = Review.objects.filter(product=product, user=request.user).exists()
        # L'utilisateur peut laisser un avis s'il a acheté le produit
        can_review = OrderItem.objects.filter(
            product=product, 
            order__user=request.user, 
            order__status='delivered'
        ).exists() and not has_reviewed
    
    # Traitement du formulaire d'avis
    if request.method == 'POST' and can_review:
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        
        if rating:
            Review.objects.create(
                product=product,
                user=request.user,
                rating=int(rating),
                comment=comment,
                is_approved=True
            )
            messages.success(request, "Votre avis a été ajouté avec succès.")
            return redirect('store:product_detail', product_id=product.id)
    
    # Produits similaires
    similar_products = Product.objects.filter(
        category=product.category,
        is_sold=False,
        sold_out=False,
        stock__gt=0
    ).exclude(id=product.id)[:4]
    
    # Vérifier si le produit est en favoris
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, product=product).exists()
    
    context = {
        'product': product,
        'reviews': reviews,
        'average_rating': average_rating,
        'can_review': can_review,
        'has_reviewed': has_reviewed,
        'similar_products': similar_products,
        'is_favorite': is_favorite,
        'favorite_count': Favorite.objects.filter(product=product).count(),
    }
    
    return render(request, 'store/product_detail.html', context)

# === Vues du panier ===
@login_required
def cart(request):
    """Affichage du panier"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    subtotal = sum(item.subtotal for item in cart_items)
    shipping_cost = Decimal('5.00')  # Coût de livraison par défaut
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
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Produit en rupture de stock'})
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
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Stock insuffisant'})
            messages.error(request, "Stock insuffisant.")
            return redirect('store:product_detail', product_id=product.id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': cart.total_items
        })
    
    messages.success(request, f"{product.name} ajouté au panier.")
    return redirect('store:cart')

@login_required
def remove_from_cart(request, item_id):
    """Supprimer un article du panier"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    
    messages.success(request, f"{product_name} retiré du panier.")
    return redirect('store:cart')

@login_required
def update_cart(request, item_id):
    """Mettre à jour la quantité d'un article"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            cart_item.delete()
            messages.success(request, "Article retiré du panier.")
        elif quantity <= cart_item.product.stock:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, "Quantité mise à jour.")
        else:
            messages.error(request, "Stock insuffisant.")
    
    return redirect('store:cart')

# === Vues de checkout ===
@login_required
def checkout(request):
    """Page de checkout"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    if not cart_items:
        messages.error(request, "Votre panier est vide.")
        return redirect('store:cart')
    
    # Calculer les totaux
    subtotal = sum(item.subtotal for item in cart_items)
    shipping_options = ShippingOption.objects.filter(is_active=True)
    addresses = Address.objects.filter(user=request.user)
    
    # Coût de livraison par défaut
    default_shipping = shipping_options.first()
    shipping_cost = default_shipping.cost if default_shipping else Decimal('0.00')
    
    # Vérifier s'il y a une réduction appliquée en session
    discount_amount = Decimal(request.session.get('discount_amount', '0.00'))
    
    total = subtotal + shipping_cost - discount_amount
    
    context = {
        'cart_items': cart_items,
        'addresses': addresses,
        'shipping_options': shipping_options,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'discount_amount': discount_amount,
        'total': total,
    }
    
    return render(request, 'store/checkout.html', context)

@login_required
def process_payment(request):
    """Traitement du paiement"""
    if request.method != 'POST':
        return redirect('store:checkout')
    
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all()
        
        if not cart_items:
            messages.error(request, "Votre panier est vide.")
            return redirect('store:cart')
        
        # Récupérer les données du formulaire
        address_mode = request.POST.get('address_mode')
        shipping_option_id = request.POST.get('shipping_option')
        payment_method = request.POST.get('payment_method')
        # Seul le paiement à la livraison est accepté
        if payment_method != 'cod':
            messages.error(request, "Seul le paiement à la livraison est disponible.")
            return redirect('store:checkout')
        
        payment_method_id = request.POST.get('payment_method_id')
        
        # Géolocalisation
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        location_description = request.POST.get('location_description', '')
        
        # Validation des champs requis
        if not shipping_option_id:
            messages.error(request, "Veuillez sélectionner une option de livraison.")
            return redirect('store:checkout')
        
        if not payment_method:
            messages.error(request, "Veuillez sélectionner une méthode de paiement.")
            return redirect('store:checkout')
        
        # Gestion de l'adresse
        shipping_address = None
        if address_mode == 'existing':
            address_id = request.POST.get('address')
            if address_id:
                shipping_address = get_object_or_404(Address, id=address_id, user=request.user)
            else:
                messages.error(request, "Veuillez sélectionner une adresse.")
                return redirect('store:checkout')
        else:
            # Créer une nouvelle adresse
            full_name = request.POST.get('full_name')
            street_address = request.POST.get('street_address')
            city = request.POST.get('city')
            postal_code = request.POST.get('postal_code')
            country = request.POST.get('country', 'Guinée')
            phone_number = request.POST.get('phone_number', '')
            
            if not all([full_name, street_address, city, postal_code]):
                messages.error(request, "Veuillez remplir tous les champs d'adresse obligatoires.")
                return redirect('store:checkout')
            
            shipping_address = Address.objects.create(
                user=request.user,
                full_name=full_name,
                street_address=street_address,
                city=city,
                postal_code=postal_code,
                country=country,
                phone_number=phone_number
            )
        
        # Récupérer l'option de livraison
        shipping_option = get_object_or_404(ShippingOption, id=shipping_option_id)
        
        # Calculer les totaux
        subtotal = sum(item.subtotal for item in cart_items)
        shipping_cost = shipping_option.cost
        discount_amount = Decimal(request.session.get('discount_amount', '0.00'))
        total = subtotal + shipping_cost - discount_amount
        
        # Traitement du paiement
        charge_id = None
        
        if payment_method == 'card':
            if not payment_method_id:
                messages.error(request, "Erreur de paiement par carte.")
                return redirect('store:checkout')
            
            try:
                # Créer le PaymentIntent avec Stripe
                intent = stripe.PaymentIntent.create(
                    amount=int(total * 100),  # Montant en centimes
                    currency='eur',
                    payment_method=payment_method_id,
                    confirmation_method='manual',
                    confirm=True,
                    return_url=request.build_absolute_uri(reverse('store:payment_success', args=[0]))
                )
                
                if intent.status == 'succeeded':
                    charge_id = intent.id
                else:
                    messages.error(request, "Erreur lors du paiement par carte.")
                    return redirect('store:checkout')
                    
            except stripe.error.StripeError as e:
                messages.error(request, f"Erreur Stripe: {str(e)}")
                return redirect('store:checkout')
        
        elif payment_method == 'paypal':
            paypal_order_id = request.POST.get('paypal_order_id')
            if paypal_order_id:
                charge_id = paypal_order_id
            else:
                messages.error(request, "Erreur de paiement PayPal.")
                return redirect('store:checkout')
        
        # Créer la commande
        order = Order.objects.create(
            user=request.user,
            total=total,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            discount_amount=discount_amount,
            shipping_address=shipping_address,
            shipping_option=shipping_option,
            payment_method='cod',
            charge_id=charge_id,
            latitude=float(latitude) if latitude else None,
            longitude=float(longitude) if longitude else None,
            location_description=location_description
        )
        
        # Créer les articles de commande
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.discounted_price,
                seller=item.product.seller
            )
            
            # Décrémenter le stock
            item.product.stock -= item.quantity
            item.product.save()
        
        # Attribuer des points de fidélité
        points_earned = int(total // 10)  # 1 point par 10€
        if points_earned > 0:
            LoyaltyPoint.objects.create(
                user=request.user,
                points=points_earned,
                description=f"Commande #{order.id}"
            )
        
        # Vider le panier
        cart_items.delete()
        
        # Nettoyer la session
        if 'discount_amount' in request.session:
            del request.session['discount_amount']
        if 'promo_code' in request.session:
            del request.session['promo_code']
        
        # Créer une notification
        Notification.objects.create(
            user=request.user,
            notification_type='order_placed',
            message=f"Votre commande #{order.id} a été passée avec succès.",
            related_object_id=order.id
        )
        
        messages.success(request, f"Commande #{order.id} passée avec succès!")
        return redirect('store:payment_success', order_id=order.id)
        
    except Exception as e:
        messages.error(request, f"Erreur lors du traitement de la commande: {str(e)}")
        return redirect('store:checkout')

def payment_success(request, order_id):
    """Page de confirmation de paiement"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'message': f"Votre commande #{order.id} a été confirmée."
    }
    
    return render(request, 'store/payment_success.html', context)

# === Vues des adresses ===
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
            
            # Rediriger vers la page précédente ou le checkout
            next_url = request.GET.get('next', reverse('accounts:profile'))
            return redirect(next_url)
    else:
        form = AddressForm()
    
    context = {
        'form': form,
        'next_url': request.GET.get('next', reverse('accounts:profile'))
    }
    
    return render(request, 'store/add_address.html', context)

# === Vues des commandes ===
@login_required
def order_history(request):
    """Historique des commandes"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'store/order_history.html', {'orders': page_obj})

@login_required
def order_detail(request, order_id):
    """Détail d'une commande"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.all()
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    
    return render(request, 'store/order_detail.html', context)

# === Vues des favoris ===
@login_required
def toggle_favorite(request, product_id):
    """Ajouter/retirer un produit des favoris"""
    product = get_object_or_404(Product, id=product_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)
    
    if not created:
        favorite.delete()
        action = 'removed'
    else:
        action = 'added'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'action': action,
            'favorite_count': Favorite.objects.filter(product=product).count()
        })
    
    return redirect('store:product_detail', product_id=product.id)

@login_required
def favorites(request):
    """Liste des favoris"""
    favorites = Favorite.objects.filter(user=request.user).order_by('-added_at')
    return render(request, 'store/favorites.html', {'favorites': favorites})

# === Vues des notifications ===
@login_required
def notifications(request):
    """Liste des notifications"""
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    return render(request, 'store/notifications.html', {'notifications': notifications})

@login_required
def mark_all_notifications_read(request):
    """Marquer toutes les notifications comme lues"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "Toutes les notifications ont été marquées comme lues.")
    return redirect('store:notifications')

# === Vues des produits (vendeur) ===
@login_required
def product_create(request):
    """Créer un nouveau produit"""
    if request.user.user_type != 'seller':
        messages.error(request, "Seuls les vendeurs peuvent ajouter des produits.")
        return redirect('store:product_list')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            
            # Créer une modération pour le produit
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
    product = get_object_or_404(Product, id=pk, seller=request.user)
    
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
    product = get_object_or_404(Product, id=pk, seller=request.user)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f"Produit '{product_name}' supprimé avec succès.")
        return redirect('store:product_list')
    
    return render(request, 'store/product_confirm_delete.html', {'product': product})

# === Vues des demandes de produits ===
@login_required
def product_request(request, product_id):
    """Faire une demande pour un produit"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductRequestForm(request.POST, user=request.user)
        if form.is_valid():
            product_request = form.save(commit=False)
            product_request.product = product
            product_request.user = request.user
            product_request.save()
            
            # Notifier le vendeur
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
    
    return render(request, 'store/request_product.html', {'form': form, 'product': product})

# === Vues des codes promo ===
@login_required
def apply_promo_code(request):
    """Appliquer un code promo"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            promo_code = data.get('promo_code', '').strip()
            
            if not promo_code:
                return JsonResponse({'success': False, 'message': 'Code promo requis.'})
            
            # Vérifier le code promo
            try:
                promo = PromoCode.objects.get(code=promo_code)
            except PromoCode.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Code promo introuvable.'})
            
            if not promo.is_valid(request.user):
                return JsonResponse({'success': False, 'message': 'Code promo invalide ou expiré.'})
            
            # Calculer la réduction
            cart = Cart.objects.get(user=request.user)
            subtotal = sum(item.subtotal for item in cart.items.all())
            discount_amount = subtotal * (promo.discount_percentage / Decimal('100'))
            
            # Sauvegarder en session
            request.session['discount_amount'] = str(discount_amount)
            request.session['promo_code'] = promo_code
            
            # Calculer le nouveau total
            shipping_cost = Decimal('5.00')  # Par défaut
            new_total = subtotal + shipping_cost - discount_amount
            
            return JsonResponse({
                'success': True,
                'discount_amount': float(discount_amount),
                'new_total': float(new_total),
                'message': 'Code promo appliqué avec succès!'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Erreur lors de l\'application du code.'})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée.'})

# === Vues de signalement ===
class ReportCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = ReportForm()
        product_id = request.GET.get('product_id')
        user_id = request.GET.get('user_id')
        
        context = {
            'form': form,
            'product_id': product_id,
            'user_id': user_id
        }
        return render(request, 'store/report_form.html', context)
    
    def post(self, request):
        form = ReportForm(request.POST, user=request.user)
        product_id = request.POST.get('product_id')
        user_id = request.POST.get('user_id')
        
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            
            if product_id:
                report.product = get_object_or_404(Product, id=product_id)
            if user_id:
                report.user = get_object_or_404(settings.AUTH_USER_MODEL, id=user_id)
            
            report.save()
            messages.success(request, "Signalement envoyé avec succès.")
            
            if product_id:
                return redirect('store:product_detail', product_id=product_id)
            else:
                return redirect('store:product_list')
        
        context = {
            'form': form,
            'product_id': product_id,
            'user_id': user_id
        }
        return render(request, 'store/report_form.html', context)

# === Vues utilitaires ===
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
                'brand': product.brand or '',
                'id': product.id
            }
            for product in products
        ]
    
    return JsonResponse({'suggestions': suggestions})

# === Gestion d'erreurs ===
def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)

# === Vues des vendeurs ===
@login_required
def seller_public_profile(request, username):
    """Profil public d'un vendeur"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    seller = get_object_or_404(User, username=username, user_type='seller')
    profile, created = SellerProfile.objects.get_or_create(user=seller)
    products = Product.objects.filter(seller=seller, is_sold=False, sold_out=False, stock__gt=0)
    ratings = SellerRating.objects.filter(seller=seller)
    
    # Calculer la note moyenne
    average_rating = ratings.aggregate(avg=Avg('rating'))['avg'] or 0
    profile.average_rating = round(average_rating, 1)
    
    context = {
        'profile': profile,
        'seller': seller,
        'products': products,
        'ratings': ratings,
    }
    
    return render(request, 'accounts/seller_public_profile.html', context)

# === Vues d'abonnement ===
@login_required
def subscription_plans(request):
    """Plans d'abonnement"""
    subscription, created = Subscription.objects.get_or_create(user=request.user)
    return render(request, 'store/subscription_plans.html', {'subscription': subscription})

@login_required
def create_subscription(request):
    """Créer un abonnement"""
    if request.method == 'POST':
        plan = request.POST.get('plan')
        
        if plan in ['free', 'basic', 'pro']:
            subscription, created = Subscription.objects.get_or_create(user=request.user)
            subscription.plan = plan
            subscription.active = True
            subscription.save()
            
            messages.success(request, f"Abonnement {plan} activé avec succès.")
        
        return redirect('store:subscription_plans')
    
    return redirect('store:subscription_plans')

# === Vues pour les livreurs ===
@login_required
def delivery_dashboard(request):
    """Tableau de bord pour les livreurs"""
    if request.user.user_type != 'delivery':
        messages.error(request, "Accès réservé aux livreurs.")
        return redirect('store:home')
    
    # Créer le profil livreur s'il n'existe pas
    delivery_profile, created = DeliveryProfile.objects.get_or_create(user=request.user)
    
    # Statistiques du livreur
    today = timezone.now().date()
    total_deliveries = Order.objects.filter(delivery_person=request.user, status='delivered').count()
    today_deliveries = Order.objects.filter(
        delivery_person=request.user, 
        delivery_completed_at__date=today
    ).count()
    pending_deliveries = Order.objects.filter(
        delivery_person=request.user, 
        status__in=['out_for_delivery']
    ).count()
    available_orders = Order.objects.filter(
        status='shipped',
        delivery_person__isnull=True
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
def delivery_orders(request):
    """Liste des commandes pour les livreurs"""
    if request.user.user_type != 'delivery':
        messages.error(request, "Accès réservé aux livreurs.")
        return redirect('store:home')
    
    # Commandes assignées au livreur
    assigned_orders = Order.objects.filter(delivery_person=request.user).order_by('-created_at')
    
    # Commandes disponibles (non assignées)
    available_orders = Order.objects.filter(
        status='shipped',
        delivery_person__isnull=True
    ).order_by('-created_at')
    
    context = {
        'assigned_orders': assigned_orders,
        'available_orders': available_orders,
    }
    
    return render(request, 'store/delivery_orders.html', context)

@login_required
def accept_delivery(request, order_id):
    """Accepter une livraison"""
    if request.user.user_type != 'delivery':
        messages.error(request, "Accès réservé aux livreurs.")
        return redirect('store:home')
    
    order = get_object_or_404(Order, id=order_id, status='shipped', delivery_person__isnull=True)
    
    if request.method == 'POST':
        order.delivery_person = request.user
        order.delivery_assigned_at = timezone.now()
        order.save()
        
        # Notifier le client
        Notification.objects.create(
            user=order.user,
            notification_type='delivery_assigned',
            message=f"Un livreur a été assigné à votre commande #{order.id}",
            related_object_id=order.id
        )
        
        messages.success(request, f"Livraison #{order.id} acceptée avec succès.")
        return redirect('store:delivery_orders')
    
    return render(request, 'store/accept_delivery.html', {'order': order})

@login_required
def start_delivery(request, order_id):
    """Démarrer une livraison"""
    if request.user.user_type != 'delivery':
        messages.error(request, "Accès réservé aux livreurs.")
        return redirect('store:home')
    
    order = get_object_or_404(Order, id=order_id, delivery_person=request.user)
    
    if request.method == 'POST':
        order.status = 'out_for_delivery'
        order.delivery_started_at = timezone.now()
        order.save()
        
        # Notifier le client
        Notification.objects.create(
            user=order.user,
            notification_type='delivery_started',
            message=f"Votre commande #{order.id} est en cours de livraison",
            related_object_id=order.id
        )
        
        messages.success(request, f"Livraison #{order.id} démarrée.")
        return redirect('store:delivery_orders')
    
    return render(request, 'store/start_delivery.html', {'order': order})

@login_required
def complete_delivery(request, order_id):
    """Terminer une livraison"""
    if request.user.user_type != 'delivery':
        messages.error(request, "Accès réservé aux livreurs.")
        return redirect('store:home')
    
    order = get_object_or_404(Order, id=order_id, delivery_person=request.user, status='out_for_delivery')
    
    if request.method == 'POST':
        order.status = 'delivered'
        order.delivery_completed_at = timezone.now()
        order.save()
        
        # Mettre à jour les statistiques du livreur
        delivery_profile = request.user.delivery_profile
        delivery_profile.total_deliveries += 1
        delivery_profile.save()
        
        # Notifier le client
        Notification.objects.create(
            user=order.user,
            notification_type='delivery_completed',
            message=f"Votre commande #{order.id} a été livrée avec succès",
            related_object_id=order.id
        )
        
        messages.success(request, f"Livraison #{order.id} terminée avec succès.")
        return redirect('store:delivery_orders')
    
    return render(request, 'store/complete_delivery.html', {'order': order})

@login_required
def update_delivery_location(request):
    """Mettre à jour la position du livreur (AJAX)"""
    if request.user.user_type != 'delivery':
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            if latitude and longitude:
                delivery_profile = request.user.delivery_profile
                delivery_profile.update_location(latitude, longitude)
                
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Coordonnées manquantes'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@login_required
def delivery_profile(request):
    """Profil du livreur"""
    if request.user.user_type != 'delivery':
        messages.error(request, "Accès réservé aux livreurs.")
        return redirect('store:home')
    
    delivery_profile, created = DeliveryProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        delivery_profile.phone_number = request.POST.get('phone_number', '')
        delivery_profile.vehicle_type = request.POST.get('vehicle_type', '')
        delivery_profile.license_number = request.POST.get('license_number', '')
        delivery_profile.is_available = request.POST.get('is_available') == 'on'
        delivery_profile.save()
        
        messages.success(request, "Profil mis à jour avec succès.")
        return redirect('store:delivery_profile')
    
    context = {
        'delivery_profile': delivery_profile,
        'ratings': DeliveryRating.objects.filter(delivery_person=request.user).order_by('-created_at')
    }
    
    return render(request, 'store/delivery_profile.html', context)