from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login
from django.urls import reverse
from django.http import JsonResponse
from django.core.files.storage import default_storage
from .forms import SellerProfileForm, ProfileForm
from .models import CustomUser, Profile, SellerProfile
from store.models import Product, Order, OrderItem, SellerStats
from django.db.models import Sum, Count, Avg
from decimal import Decimal

def vendor_signup(request):
    """Page d'inscription vendeur"""
    if request.method == 'POST':
        from .forms import VendorSignUpForm
        form = VendorSignUpForm(request.POST)
        if form.is_valid():
            user = form.save(request)
            messages.success(
                request, 
                f"Bienvenue {user.first_name} ! Votre compte vendeur a été créé avec succès. "
                "Vous pouvez maintenant ajouter vos premiers produits."
            )
            # Connecter automatiquement l'utilisateur
            login(request, user)
            return redirect('vendor:dashboard')
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        from .forms import VendorSignUpForm
        form = VendorSignUpForm()
    
    return render(request, 'accounts/vendor_signup.html', {'form': form})

def buyer_signup(request):
    """Page d'inscription acheteur"""
    if request.method == 'POST':
        from .forms import BuyerSignUpForm
        form = BuyerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save(request)
            messages.success(
                request, 
                f"Bienvenue {user.username} ! Votre compte a été créé avec succès."
            )
            login(request, user)
            return redirect('store:home')
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        from .forms import BuyerSignUpForm
        form = BuyerSignUpForm()
    
    return render(request, 'accounts/buyer_signup.html', {'form': form})

def signup_choice(request):
    """Page de choix du type de compte"""
    return render(request, 'accounts/signup_choice.html')

@login_required
def profile(request):
    """Page de profil général"""
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour avec succès !")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Erreur lors de la mise à jour du profil.")
    else:
        form = ProfileForm(instance=profile)
    
    # Données spécifiques selon le type d'utilisateur
    context = {
        'form': form,
        'profile': profile,
    }
    
    if request.user.user_type == 'seller':
        # Statistiques vendeur
        context.update({
            'total_products': Product.objects.filter(seller=request.user).count(),
            'active_products': Product.objects.filter(
                seller=request.user, 
                is_sold=False, 
                sold_out=False, 
                stock__gt=0
            ).count(),
            'total_orders': Order.objects.filter(
                items__product__seller=request.user
            ).distinct().count(),
            'total_revenue': OrderItem.objects.filter(
                product__seller=request.user,
                order__status='delivered'
            ).aggregate(total=Sum('price'))['total'] or Decimal('0'),
        })
    
    return render(request, 'accounts/profile.html', context)

@login_required
def vendor_profile(request):
    """Page de profil vendeur spécifique"""
    if request.user.user_type != 'seller':
        messages.error(request, "Accès réservé aux vendeurs.")
        return redirect('accounts:profile')
    
    seller_profile = request.user.seller_profile
    
    if request.method == 'POST':
        form = SellerProfileForm(request.POST, request.FILES, instance=seller_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil vendeur mis à jour avec succès !")
            return redirect('accounts:vendor_profile')
        else:
            messages.error(request, "Erreur lors de la mise à jour.")
    else:
        form = SellerProfileForm(instance=seller_profile)
    
    # Statistiques détaillées
    stats, created = SellerStats.objects.get_or_create(seller=request.user)
    if created or stats.last_updated < timezone.now() - timedelta(hours=1):
        stats.update_stats()
    
    context = {
        'form': form,
        'seller_profile': seller_profile,
        'stats': stats,
        'recent_orders': Order.objects.filter(
            items__product__seller=request.user
        ).distinct().order_by('-created_at')[:5],
        'top_products': Product.objects.filter(
            seller=request.user
        ).order_by('-sales_count')[:5],
    }
    
    return render(request, 'accounts/vendor_profile.html', context)

@login_required
def vendor_public_profile(request, username):
    """Profil public d'un vendeur"""
    vendor = get_object_or_404(CustomUser, username=username, user_type='seller')
    seller_profile = vendor.seller_profile
    
    # Produits du vendeur
    products = Product.objects.filter(
        seller=vendor,
        is_sold=False,
        sold_out=False,
        stock__gt=0
    ).order_by('-created_at')[:12]
    
    # Évaluations du vendeur
    from store.models import SellerRating
    ratings = SellerRating.objects.filter(seller=vendor).order_by('-created_at')[:10]
    
    context = {
        'vendor': vendor,
        'seller_profile': seller_profile,
        'products': products,
        'ratings': ratings,
        'total_products': Product.objects.filter(seller=vendor).count(),
        'average_rating': ratings.aggregate(avg=Avg('rating'))['avg'] or 0,
        'total_sales': seller_profile.total_sales,
    }
    
    return render(request, 'accounts/vendor_public_profile.html', context)

@login_required
def update_profile_picture(request):
    """Mise à jour de la photo de profil"""
    if request.method == 'POST' and 'profile_picture' in request.FILES:
        profile = request.user.profile
        
        # Supprimer l'ancienne photo
        if profile.profile_picture:
            default_storage.delete(profile.profile_picture.name)
        
        profile.profile_picture = request.FILES['profile_picture']
        profile.save()
        
        messages.success(request, "Photo de profil mise à jour avec succès !")
    else:
        messages.error(request, "Erreur lors de la mise à jour de la photo.")
    
    return redirect('accounts:profile')

@login_required
def delete_account(request):
    """Suppression du compte utilisateur"""
    if request.method == 'POST':
        user = request.user
        
        # Vérifications spéciales pour les vendeurs
        if user.user_type == 'seller':
            # Vérifier s'il y a des commandes en cours
            pending_orders = Order.objects.filter(
                items__product__seller=user,
                status__in=['pending', 'processing', 'shipped']
            ).distinct().count()
            
            if pending_orders > 0:
                messages.error(
                    request, 
                    f"Impossible de supprimer le compte. Vous avez {pending_orders} commande(s) en cours. "
                    "Veuillez d'abord terminer toutes vos commandes."
                )
                return redirect('accounts:profile')
        
        # Supprimer le compte
        username = user.username
        user.delete()
        
        messages.success(request, f"Le compte {username} a été supprimé avec succès.")
        return redirect('store:home')
    
    return redirect('accounts:profile')

def vendor_verification_status(request):
    """API pour vérifier le statut de vérification vendeur"""
    if not request.user.is_authenticated or request.user.user_type != 'seller':
        return JsonResponse({'error': 'Non autorisé'}, status=403)
    
    seller_profile = request.user.seller_profile
    
    return JsonResponse({
        'is_verified': request.user.is_verified_seller,
        'profile_complete': bool(
            seller_profile.business_name and 
            seller_profile.business_description and 
            seller_profile.business_address
        ),
        'documents_uploaded': bool(
            seller_profile.business_license or 
            seller_profile.tax_number
        ),
        'can_sell': request.user.is_verified_seller and seller_profile.is_active,
    })