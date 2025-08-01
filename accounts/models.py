from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('buyer', 'Acheteur'),
        ('seller', 'Vendeur'),
        ('delivery', 'Livreur'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='buyer')
    email = models.EmailField(unique=True)
    
    # Champs spécifiques vendeur
    is_verified_seller = models.BooleanField(default=False, help_text="Vendeur vérifié par l'admin")
    seller_since = models.DateTimeField(null=True, blank=True, help_text="Date de début en tant que vendeur")
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    address = models.TextField(blank=True, verbose_name="Adresse principale")
    phone = models.CharField(max_length=15, blank=True, verbose_name="Téléphone")
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True, verbose_name="Photo de profil")
    description = models.TextField(blank=True, verbose_name="Description", help_text="Décrivez votre boutique ou vos services.")

    def __str__(self):
        return f"Profil de {self.user.username}"

class SellerProfile(models.Model):
    """Profil spécifique aux vendeurs avec informations business"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='seller_profile')
    
    # Informations personnelles
    first_name = models.CharField(max_length=100, blank=True, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, blank=True, verbose_name="Nom")
    
    # Informations business
    business_name = models.CharField(max_length=200, blank=True, verbose_name="Nom de l'entreprise")
    business_description = models.TextField(blank=True, verbose_name="Description de l'entreprise")
    business_address = models.TextField(blank=True, verbose_name="Adresse de l'entreprise")
    business_phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone professionnel")
    business_email = models.EmailField(blank=True, verbose_name="Email professionnel")
    
    # Documents et vérification
    business_license = models.CharField(max_length=100, blank=True, verbose_name="Numéro de licence")
    tax_number = models.CharField(max_length=100, blank=True, verbose_name="Numéro fiscal")
    
    # Médias
    profile_picture = models.ImageField(upload_to='seller_profiles/', blank=True, null=True, verbose_name="Photo de profil")
    business_logo = models.ImageField(upload_to='business_logos/', blank=True, null=True, verbose_name="Logo de l'entreprise")
    
    # Paramètres
    accepts_returns = models.BooleanField(default=True, verbose_name="Accepte les retours")
    return_policy = models.TextField(blank=True, verbose_name="Politique de retour")
    shipping_policy = models.TextField(blank=True, verbose_name="Politique de livraison")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Profil actif")
    
    class Meta:
        verbose_name = "Profil vendeur"
        verbose_name_plural = "Profils vendeurs"
    
    def __str__(self):
        return f"Vendeur: {self.business_name or self.user.username}"
    
    @property
    def display_name(self):
        """Nom d'affichage du vendeur"""
        if self.business_name:
            return self.business_name
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.user.username
    
    @property
    def total_sales(self):
        """Total des ventes du vendeur"""
        from store.models import OrderItem
        return OrderItem.objects.filter(
            product__seller=self.user,
            order__status='delivered'
        ).aggregate(total=models.Sum('price'))['total'] or 0
    
    @property
    def total_products(self):
        """Nombre total de produits"""
        return self.user.products.count()
    
    @property
    def active_products(self):
        """Nombre de produits actifs"""
        return self.user.products.filter(
            is_sold=False,
            sold_out=False,
            stock__gt=0
        ).count()
    
    @property
    def average_rating(self):
        """Note moyenne du vendeur"""
        from store.models import SellerRating
        ratings = SellerRating.objects.filter(seller=self.user)
        if ratings.exists():
            return round(ratings.aggregate(avg=models.Avg('rating'))['avg'], 1)
        return 0

class Address(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='addresses')
    address_line1 = models.CharField(max_length=255, verbose_name="Ligne d'adresse 1")
    address_line2 = models.CharField(max_length=255, blank=True, verbose_name="Ligne d'adresse 2")
    city = models.CharField(max_length=100, verbose_name="Ville")
    postal_code = models.CharField(max_length=20, verbose_name="Code postal")
    country = models.CharField(max_length=100, verbose_name="Pays")
    is_default = models.BooleanField(default=False, verbose_name="Adresse par défaut")

    def __str__(self):
        return f"{self.address_line1}, {self.city}, {self.country}"

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(profile=self.profile, is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)