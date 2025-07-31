from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os

# === Modèle Category ===
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def __str__(self):
        return self.name

# === Modèle Discount ===
class Discount(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='discounts')
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Pourcentage de réduction (0-100)"
    )
    start_date = models.DateTimeField(help_text="Date de début de la réduction")
    end_date = models.DateTimeField(help_text="Date de fin de la réduction")
    is_active = models.BooleanField(default=True, help_text="Indique si la réduction est active")

    class Meta:
        verbose_name = "Réduction"
        verbose_name_plural = "Réductions"
        ordering = ['-start_date']

    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("La date de fin doit être postérieure à la date de début.")
        if self.percentage <= 0 or self.percentage > 100:
            raise ValidationError("Le pourcentage de réduction doit être entre 0 et 100.")
        super().clean()

    def __str__(self):
        return f"Réduction {self.percentage}% sur {self.product.name}"

# === Modèle Product ===
class Product(models.Model):
    SIZE_CHOICES = [
        ('', 'Sélectionner une taille'),
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Double Extra Large'),
        ('XXXL', 'Triple Extra Large'),
        ('One Size', 'Taille unique'),
        ('Custom', 'Taille personnalisée'),
    ]

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    image1 = models.ImageField(upload_to='products/', blank=True, null=True)
    image2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image3 = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)
    sales_count = models.PositiveIntegerField(default=0, help_text="Nombre total d'unités vendues")
    is_sold = models.BooleanField(default=False)
    sold_out = models.BooleanField(default=False)
    size = models.CharField(max_length=20, choices=SIZE_CHOICES, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    material = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def discounted_price(self):
        current_time = timezone.now()
        active_discount = self.discounts.filter(
            is_active=True, 
            start_date__lte=current_time, 
            end_date__gte=current_time
        ).order_by('-percentage').first()
        
        if active_discount:
            discount_amount = self.price * (active_discount.percentage / Decimal('100'))
            return self.price - discount_amount
        return self.price

    @property
    def active_discount_percentage(self):
        current_time = timezone.now()
        active_discount = self.discounts.filter(
            is_active=True, 
            start_date__lte=current_time, 
            end_date__gte=current_time
        ).order_by('-percentage').first()
        return active_discount.percentage if active_discount else 0

    @property
    def is_sold_out(self):
        return self.stock == 0 or self.is_sold or self.sold_out

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            return round(sum(review.rating for review in reviews) / reviews.count(), 1)
        return 0

# === Modèles Cart et CartItem ===
class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Panier"
        verbose_name_plural = "Paniers"

    def __str__(self):
        return f"Panier de {self.user.username}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Article de panier"
        verbose_name_plural = "Articles de panier"
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def subtotal(self):
        return self.quantity * self.product.discounted_price

# === Modèle ShippingOption ===
class ShippingOption(models.Model):
    name = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_days = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Option de livraison"
        verbose_name_plural = "Options de livraison"

    def __str__(self):
        return f"{self.name} - {self.cost}€ ({self.estimated_days} jours)"

# === Modèle Address ===
class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=100)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Adresse"
        verbose_name_plural = "Adresses"
        ordering = ['-is_default']

    def __str__(self):
        return f"{self.full_name}, {self.street_address}, {self.city}"

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

# === Modèles Order et OrderItem ===
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours de traitement'),
        ('shipped', 'Expédié'),
        ('out_for_delivery', 'En cours de livraison'),
        ('delivered', 'Livré'),
        ('cancelled', 'Annulé'),
    ]
    PAYMENT_METHODS = [
        ('cod', 'Paiement à la livraison'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_sold')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True, blank=True)
    shipping_option = models.ForeignKey('ShippingOption', on_delete=models.SET_NULL, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='card')
    charge_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Géolocalisation
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_description = models.TextField(blank=True, null=True)

    # Livreur assigné
    delivery_person = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='delivery_orders',
        limit_choices_to={'user_type': 'delivery'}
    )
    delivery_assigned_at = models.DateTimeField(null=True, blank=True)
    delivery_started_at = models.DateTimeField(null=True, blank=True)
    delivery_completed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ['-created_at']

    def __str__(self):
        return f"Commande {self.id} par {self.user.username}"

    @property
    def can_assign_delivery(self):
        """Vérifie si la commande peut être assignée à un livreur"""
        return self.status in ['processing', 'shipped'] and not self.delivery_person
    
    @property
    def delivery_status(self):
        """Retourne le statut de livraison"""
        if not self.delivery_person:
            return "Non assigné"
        elif self.status == 'delivered':
            return "Livré"
        elif self.delivery_started_at:
            return "En cours de livraison"
        elif self.delivery_assigned_at:
            return "Assigné"
        return "En attente"
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')

    class Meta:
        verbose_name = "Article de commande"
        verbose_name_plural = "Articles de commande"

    def __str__(self):
        return f"{self.quantity} x {self.product.name} dans la commande {self.order.id}"

# === Modèle Favorite ===
class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} a favorisé {self.product.name}"

# === Modèle Review ===
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reply = models.TextField(max_length=500, blank=True, null=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"Avis de {self.user.username} sur {self.product.name} ({self.rating}/5)"

# === Modèle ProductRequest ===
class ProductRequest(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='requests')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_requests', null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    desired_quantity = models.PositiveIntegerField(default=1)
    desired_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_notified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Demande de produit"
        verbose_name_plural = "Demandes de produits"
        ordering = ['-created_at']

    def __str__(self):
        return f"Demande de {self.user.username if self.user else self.email} pour {self.product.name}"

# === Modèle ProductView ===
class ProductView(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_views')
    view_date = models.DateTimeField(auto_now_add=True)
    view_count = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Vue produit"
        verbose_name_plural = "Vues produit"
        unique_together = ('product', 'view_date')

    def __str__(self):
        return f"{self.product.name} vu le {self.view_date.strftime('%Y-%m-%d')} ({self.view_count} vues)"

# === Modèle Notification ===
class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification pour {self.user.username}: {self.message[:50]}..."

# === Modèles Conversation et Message ===
class Conversation(models.Model):
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations_initiated')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations_received')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        unique_together = ('initiator', 'recipient', 'product')

    def __str__(self):
        return f"Conversation entre {self.initiator} et {self.recipient}"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ['sent_at']

    def __str__(self):
        return f"Message de {self.sender}"

# === Modèle SellerRating ===
class SellerRating(models.Model):
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings_received')
    rater = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings_given')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Note vendeur"
        verbose_name_plural = "Notes vendeurs"
        unique_together = ('seller', 'rater', 'order')

    def __str__(self):
        return f"Note {self.rating}/5 par {self.rater}"

# === Modèle SellerProfile ===
class SellerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller_profile')
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_address = models.CharField(max_length=255, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    class Meta:
        verbose_name = "Profil vendeur"
        verbose_name_plural = "Profils vendeurs"

    def __str__(self):
        return f"Profil de {self.user.username}"

class DeliveryProfile(models.Model):
    """Profil spécifique aux livreurs"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='delivery_profile',
        limit_choices_to={'user_type': 'delivery'}
    )
    phone_number = models.CharField(max_length=20, verbose_name="Numéro de téléphone")
    vehicle_type = models.CharField(
        max_length=20,
        choices=[
            ('bike', 'Vélo'),
            ('motorbike', 'Moto'),
            ('car', 'Voiture'),
            ('van', 'Camionnette'),
        ],
        verbose_name="Type de véhicule"
    )
    license_number = models.CharField(max_length=50, blank=True, verbose_name="Numéro de permis")
    is_available = models.BooleanField(default=True, verbose_name="Disponible")
    current_latitude = models.FloatField(null=True, blank=True)
    current_longitude = models.FloatField(null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0, verbose_name="Note moyenne")
    total_deliveries = models.PositiveIntegerField(default=0, verbose_name="Nombre de livraisons")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Profil livreur"
        verbose_name_plural = "Profils livreurs"
    
    def __str__(self):
        return f"Livreur {self.user.username}"
    
    def update_location(self, latitude, longitude):
        """Met à jour la position du livreur"""
        self.current_latitude = latitude
        self.current_longitude = longitude
        self.last_location_update = timezone.now()
        self.save(update_fields=['current_latitude', 'current_longitude', 'last_location_update'])

class DeliveryRating(models.Model):
    """Évaluation des livreurs par les clients"""
    delivery_person = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='delivery_ratings'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='given_delivery_ratings'
    )
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery_rating')
    rating = models.PositiveIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        verbose_name="Note"
    )
    comment = models.TextField(blank=True, verbose_name="Commentaire")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Évaluation livreur"
        verbose_name_plural = "Évaluations livreurs"
        unique_together = ['delivery_person', 'customer', 'order']
    
    def __str__(self):
        return f"Note {self.rating}/5 pour {self.delivery_person.username}"

# === Modèle Subscription ===
class Subscription(models.Model):
    PLAN_CHOICES = [
        ('free', 'Gratuit'),
        ('basic', 'Basique'),
        ('pro', 'Professionnel'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default='free')
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"

    def __str__(self):
        return f"Abonnement {self.plan} de {self.user}"

# === Modèles de Géolocalisation pour la Guinée ===
class GuineaRegion(models.Model):
    """Régions administratives de la Guinée"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom de la région")
    code = models.CharField(max_length=10, unique=True, verbose_name="Code région")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Région"
        verbose_name_plural = "Régions"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class GuineaPrefecture(models.Model):
    """Préfectures/Communes de la Guinée"""
    region = models.ForeignKey(GuineaRegion, on_delete=models.CASCADE, related_name='prefectures')
    name = models.CharField(max_length=100, verbose_name="Nom de la préfecture")
    code = models.CharField(max_length=10, verbose_name="Code préfecture")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Préfecture"
        verbose_name_plural = "Préfectures"
        ordering = ['name']
        unique_together = ['region', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.region.name})"

class GuineaQuartier(models.Model):
    """Quartiers/Secteurs"""
    prefecture = models.ForeignKey(GuineaPrefecture, on_delete=models.CASCADE, related_name='quartiers')
    name = models.CharField(max_length=100, verbose_name="Nom du quartier")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Quartier"
        verbose_name_plural = "Quartiers"
        ordering = ['name']
        unique_together = ['prefecture', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.prefecture.name})"

class GuineaAddress(models.Model):
    """Adresses spécifiques à la Guinée avec système collaboratif"""
    STATUS_CHOICES = [
        ('pending', 'En attente de validation'),
        ('validated', 'Validée'),
        ('rejected', 'Rejetée'),
    ]
    
    # Informations géographiques
    region = models.ForeignKey(GuineaRegion, on_delete=models.CASCADE, related_name='addresses')
    prefecture = models.ForeignKey(GuineaPrefecture, on_delete=models.CASCADE, related_name='addresses')
    quartier = models.ForeignKey(GuineaQuartier, on_delete=models.CASCADE, related_name='addresses')
    
    # Description locale
    description = models.TextField(
        verbose_name="Description de l'adresse",
        help_text="Ex: 123 près de la mosquée Diaouné, en face du marché"
    )
    landmark = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name="Point de repère",
        help_text="Ex: Mosquée, École, Marché, etc."
    )
    
    # Coordonnées GPS
    latitude = models.FloatField(
        validators=[MinValueValidator(7.0), MaxValueValidator(13.0)],
        verbose_name="Latitude"
    )
    longitude = models.FloatField(
        validators=[MinValueValidator(-15.0), MaxValueValidator(-7.0)],
        verbose_name="Longitude"
    )
    
    # Métadonnées
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_addresses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    usage_count = models.PositiveIntegerField(default=0, verbose_name="Nombre d'utilisations")
    
    # Photo optionnelle
    photo = models.ImageField(upload_to='addresses/photos/', blank=True, null=True)
    
    class Meta:
        verbose_name = "Adresse guinéenne"
        verbose_name_plural = "Adresses guinéennes"
        ordering = ['-usage_count', '-created_at']
        unique_together = ['latitude', 'longitude']
    
    def __str__(self):
        return f"{self.description[:50]} - {self.quartier.name}"
    
    @property
    def google_maps_link(self):
        """Génère un lien Google Maps"""
        return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"

class UserLocation(models.Model):
    """Localisation d'un utilisateur avec photo et description"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='store_locations')
    guinea_address = models.ForeignKey(GuineaAddress, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Coordonnées exactes
    latitude = models.FloatField(verbose_name="Latitude")
    longitude = models.FloatField(verbose_name="Longitude")
    
    # Description personnalisée
    description = models.TextField(
        verbose_name="Description personnalisée",
        help_text="Décrivez précisément votre localisation"
    )
    
    # Photo avec géolocalisation
    photo = models.ImageField(upload_to='user_locations/', blank=True, null=True)
    photo_latitude = models.FloatField(null=True, blank=True)
    photo_longitude = models.FloatField(null=True, blank=True)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Localisation utilisateur"
        verbose_name_plural = "Localisations utilisateurs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.description[:50]}"
    
    @property
    def google_maps_link(self):
        """Génère un lien Google Maps"""
        return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"

class DeliveryLocation(models.Model):
    """Localisation spécifique pour les livraisons"""
    user_location = models.OneToOneField(UserLocation, on_delete=models.CASCADE, related_name='delivery_info')
    access_instructions = models.TextField(
        verbose_name="Instructions d'accès",
        help_text="Comment accéder à cette adresse (étage, porte, etc.)"
    )
    contact_phone = models.CharField(max_length=20, verbose_name="Téléphone de contact")
    is_default = models.BooleanField(default=False, verbose_name="Adresse par défaut")
    
    class Meta:
        verbose_name = "Adresse de livraison"
        verbose_name_plural = "Adresses de livraison"
    
    def __str__(self):
        return f"Livraison - {self.user_location.description[:30]}"

# === Signaux ===
@receiver(post_save, sender=Order)
def set_order_seller(sender, instance, created, **kwargs):
    if created and not instance.seller:
        first_item = instance.items.first()
        if first_item and first_item.product and first_item.product.seller:
            instance.seller = first_item.product.seller
            instance.save(update_fields=['seller'])