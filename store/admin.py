from django.contrib import admin
from .models import (
    Product, Category, Cart, CartItem, Address, ShippingOption, Order, OrderItem, 
    Favorite, Review, Notification, ProductView, ProductRequest,
    GuineaRegion, GuineaPrefecture, GuineaQuartier, GuineaAddress, UserLocation, DeliveryLocation
)
from marketing.admin import admin_site  # Importe admin_site depuis marketing

@admin.register(Product, site=admin_site)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'seller', 'category', 'price', 'stock', 'size', 'brand', 'color', 'material']
    list_filter = ['category', 'seller', 'size', 'brand', 'color', 'material']
    search_fields = ['name', 'description', 'brand', 'color', 'material']
    fieldsets = (
        (None, {
            'fields': ('seller', 'category', 'name', 'description', 'price', 'stock')
        }),
        ('Images', {
            'fields': ('image1', 'image2', 'image3')
        }),
        ('Détails supplémentaires', {
            'fields': ('size', 'brand', 'color', 'material')
        }),
        ('Statut et réduction', {
            'fields': ('discount_percentage', 'is_sold', 'sold_out')
        }),
    )

@admin.register(Category, site=admin_site)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']

@admin.register(Cart, site=admin_site)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']

@admin.register(CartItem, site=admin_site)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity']

@admin.register(Address, site=admin_site)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'city', 'postal_code', 'is_default']

@admin.register(ShippingOption, site=admin_site)
class ShippingOptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'cost', 'estimated_days', 'is_active']

@admin.register(Order, site=admin_site)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'seller', 'total', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'user__username', 'seller__username']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']  # Ajouté comme champs en lecture seule
    fieldsets = (
        ('Informations de base', {
            'fields': ('user', 'seller', 'total', 'shipping_address', 'shipping_option', 'status', 'payment_method')
        }),
        ('Dates (lecture seule)', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(OrderItem, site=admin_site)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']

@admin.register(Favorite, site=admin_site)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']

@admin.register(Review, site=admin_site)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']

@admin.register(Notification, site=admin_site)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'created_at', 'is_read']

@admin.register(ProductView, site=admin_site)
class ProductViewAdmin(admin.ModelAdmin):
    list_display = ['product', 'view_date', 'view_count']

@admin.register(ProductRequest, site=admin_site)
class ProductRequestAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'email', 'message', 'desired_quantity', 'desired_date', 'created_at']
    list_filter = ['product', 'user']
    search_fields = ['product__name', 'email', 'message']
    readonly_fields = ['created_at']

# === Administration de la géolocalisation ===
@admin.register(GuineaRegion, site=admin_site)
class GuineaRegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']
    ordering = ['name']

@admin.register(GuineaPrefecture, site=admin_site)
class GuineaPrefectureAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'code', 'created_at']
    list_filter = ['region']
    search_fields = ['name', 'code']
    ordering = ['region__name', 'name']

@admin.register(GuineaQuartier, site=admin_site)
class GuineaQuartierAdmin(admin.ModelAdmin):
    list_display = ['name', 'prefecture', 'get_region', 'created_at']
    list_filter = ['prefecture__region', 'prefecture']
    search_fields = ['name', 'prefecture__name']
    ordering = ['prefecture__region__name', 'prefecture__name', 'name']
    
    def get_region(self, obj):
        return obj.prefecture.region.name
    get_region.short_description = 'Région'

@admin.register(GuineaAddress, site=admin_site)
class GuineaAddressAdmin(admin.ModelAdmin):
    list_display = ['description', 'quartier', 'get_prefecture', 'get_region', 'status', 'usage_count', 'created_by']
    list_filter = ['status', 'region', 'prefecture', 'quartier']
    search_fields = ['description', 'landmark']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    ordering = ['-usage_count', '-created_at']
    
    fieldsets = (
        ('Localisation', {
            'fields': ('region', 'prefecture', 'quartier')
        }),
        ('Description', {
            'fields': ('description', 'landmark')
        }),
        ('Coordonnées GPS', {
            'fields': ('latitude', 'longitude')
        }),
        ('Métadonnées', {
            'fields': ('created_by', 'status', 'usage_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Photo', {
            'fields': ('photo',),
            'classes': ('collapse',)
        })
    )
    
    def get_prefecture(self, obj):
        return obj.prefecture.name
    get_prefecture.short_description = 'Préfecture'
    
    def get_region(self, obj):
        return obj.region.name
    get_region.short_description = 'Région'

@admin.register(UserLocation, site=admin_site)
class UserLocationAdmin(admin.ModelAdmin):
    list_display = ['user', 'description', 'guinea_address', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'description']
    readonly_fields = ['photo_latitude', 'photo_longitude', 'created_at']
    ordering = ['-created_at']

@admin.register(DeliveryLocation, site=admin_site)
class DeliveryLocationAdmin(admin.ModelAdmin):
    list_display = ['user_location', 'contact_phone', 'is_default']
    list_filter = ['is_default']
    search_fields = ['user_location__user__username', 'contact_phone']

@admin.register(DeliveryProfile, site=admin_site)
class DeliveryProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'vehicle_type', 'is_available', 'rating', 'total_deliveries']
    list_filter = ['vehicle_type', 'is_available', 'created_at']
    search_fields = ['user__username', 'phone_number']
    readonly_fields = ['rating', 'total_deliveries', 'last_location_update']
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('user', 'phone_number')
        }),
        ('Véhicule', {
            'fields': ('vehicle_type', 'license_number')
        }),
        ('Statut', {
            'fields': ('is_available',)
        }),
        ('Localisation', {
            'fields': ('current_latitude', 'current_longitude', 'last_location_update'),
            'classes': ('collapse',)
        }),
        ('Statistiques', {
            'fields': ('rating', 'total_deliveries'),
            'classes': ('collapse',)
        })
    )

@admin.register(DeliveryRating, site=admin_site)
class DeliveryRatingAdmin(admin.ModelAdmin):
    list_display = ['delivery_person', 'customer', 'order', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['delivery_person__username', 'customer__username']
    readonly_fields = ['created_at']