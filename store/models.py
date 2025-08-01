from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from PIL import Image
import os
import uuid
from datetime import timedelta

# === Modèle Category ===
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('store:category_products', kwargs={'slug': self.slug})

    @property
    def product_count(self):
        return self.products.filter(is_active=True, stock__gt=0).count()

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

    CONDITION_CHOICES = [
        ('new', 'Neuf'),
        ('like_new', 'Comme neuf'),
        ('good', 'Bon état'),
        ('fair', 'État correct'),
        ('poor', 'Mauvais état'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente de modération'),
        ('active', 'Actif'),
        ('inactive', 'Inactif'),
        ('rejected', 'Rejeté'),
    ]

    # Informations de base
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    # Détails produit
    name = models.CharField(max_length=255, verbose_name="Nom du produit")
    description = models.TextField(verbose_name="Description")
    short_description = models.CharField(max_length=500, blank=True, verbose_name="Description courte")
    
    # Prix et stock
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix")
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Prix de comparaison")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Prix de revient")
    stock = models.PositiveIntegerField(verbose_name="Stock")
    low_stock_threshold = models.PositiveIntegerField(default=5, verbose_name="Seuil stock faible")
    
    # Images
    image1 = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Image principale")
    image2 = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Image 2")
    image3 = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Image 3")
    image4 = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Image 4")
    image5 = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Image 5")
    
    # Attributs produit
    size = models.CharField(max_length=20, choices=SIZE_CHOICES, blank=True, null=True, verbose_name="Taille")
    brand = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marque")
    color = models.CharField(max_length=50, blank=True, null=True, verbose_name="Couleur")
    material = models.CharField(max_length=100, blank=True, null=True, verbose_name="Matériau")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new', verbose_name="État")
    
    # Dimensions et poids
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="Poids (kg)")
    length = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="Longueur (cm)")
    width = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="Largeur (cm)")
    height = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="Hauteur (cm)")
    
    # SEO et référencement
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    meta_title = models.CharField(max_length=255, blank=True, verbose_name="Titre SEO")
    meta_description = models.TextField(max_length=500, blank=True, verbose_name="Description SEO")
    tags = models.CharField(max_length=500, blank=True, verbose_name="Tags (séparés par des virgules)")
    
    # Statut et modération
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Statut")
    is_featured = models.BooleanField(default=False, verbose_name="Produit vedette")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    # Statistiques
    views = models.PositiveIntegerField(default=0, verbose_name="Vues")
    sales_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de ventes")
    favorites_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de favoris")
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Générer le slug automatiquement
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Définir la date de publication
        if self.status == 'active' and not self.published_at:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:product_detail', kwargs={'slug': self.slug})

    @property
    def is_in_stock(self):
        return self.stock > 0 and self.is_active

    @property
    def is_low_stock(self):
        return self.stock <= self.low_stock_threshold

    @property
    def discount_percentage(self):
        if self.compare_price and self.compare_price > self.price:
            return round(((self.compare_price - self.price) / self.compare_price) * 100, 1)
        return 0

    @property
    def profit_margin(self):
        if self.cost_price:
            return round(((self.price - self.cost_price) / self.price) * 100, 1)
        return 0

    @property
    def average_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            return round(sum(review.rating for review in reviews) / reviews.count(), 1)
        return 0

    @property
    def review_count(self):
        return self.reviews.filter(is_approved=True).count()

    @property
    def main_image(self):
        return self.image1 or self.image2 or self.image3 or self.image4 or self.image5

    def get_all_images(self):
        images = []
        for i in range(1, 6):
            image = getattr(self, f'image{i}')
            if image:
                images.append(image)
        return images

    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])

    def can_be_edited_by(self, user):
        return self.seller == user or user.is_staff

# === Modèle ProductImage (pour plus de flexibilité) ===
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to='products/additional/')
    alt_text = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"Image pour {self.product.name}"

# === Modèle ProductVariant (pour les variantes) ===
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100, verbose_name="Nom de la variante")
    sku = models.CharField(max_length=100, unique=True, verbose_name="SKU")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix")
    stock = models.PositiveIntegerField(verbose_name="Stock")
    size = models.CharField(max_length=20, choices=Product.SIZE_CHOICES, blank=True)
    color = models.CharField(max_length=50, blank=True)
    image = models.ImageField(upload_to='products/variants/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Variante de produit"
        verbose_name_plural = "Variantes de produits"
        unique_together = ['product', 'name']

    def __str__(self):
        return f"{self.product.name} - {self.name}"

# === Modèle ProductModeration ===
class ProductModeration(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
        ('changes_requested', 'Modifications demandées'),
    ]

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='moderation')
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='moderated_products')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(blank=True, verbose_name="Raison/Commentaires")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Modération de produit"
        verbose_name_plural = "Modérations de produits"

    def __str__(self):
        return f"Modération {self.product.name} - {self.status}"

# === Modèles existants (Cart, Order, etc.) ===
class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Article de panier"
        verbose_name_plural = "Articles de panier"
        unique_together = ('cart', 'product', 'variant')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def unit_price(self):
        return self.variant.price if self.variant else self.product.price

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

# === Modèle Order ===
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('processing', 'En préparation'),
        ('shipped', 'Expédiée'),
        ('delivered', 'Livrée'),
        ('cancelled', 'Annulée'),
        ('refunded', 'Remboursée'),
    ]

    # Informations de base
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Montants
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ['-created_at']

    def __str__(self):
        return f"Commande {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        import random
        import string
        while True:
            number = ''.join(random.choices(string.digits, k=8))
            if not Order.objects.filter(order_number=number).exists():
                return number

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sold_items')
    
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Article de commande"
        verbose_name_plural = "Articles de commande"

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

# === Modèle Review ===
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    title = models.CharField(max_length=255, blank=True, verbose_name="Titre de l'avis")
    comment = models.TextField(verbose_name="Commentaire")
    
    # Réponse du vendeur
    seller_reply = models.TextField(blank=True, verbose_name="Réponse du vendeur")
    seller_reply_date = models.DateTimeField(null=True, blank=True)
    
    # Modération
    is_approved = models.BooleanField(default=False)
    is_verified_purchase = models.BooleanField(default=False)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"Avis de {self.user.username} sur {self.product.name}"

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
        return f"{self.user.username} ♥ {self.product.name}"

# === Modèle Notification ===
class Notification(models.Model):
    TYPE_CHOICES = [
        ('order_placed', 'Nouvelle commande'),
        ('order_updated', 'Commande mise à jour'),
        ('product_approved', 'Produit approuvé'),
        ('product_rejected', 'Produit rejeté'),
        ('review_added', 'Nouvel avis'),
        ('stock_low', 'Stock faible'),
        ('general', 'Général'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='general')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Lien optionnel
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification pour {self.user.username}: {self.title}"