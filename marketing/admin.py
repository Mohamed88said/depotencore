from django.contrib import admin
from .models import LoyaltyPoint, Reward, PromoCode
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.db.models import Count, Sum

# Définition des classes Admin
class LoyaltyPointAdmin(admin.ModelAdmin):
    list_display = ['user', 'points', 'earned_at', 'expires_at', 'description']
    list_filter = ['user', 'earned_at', 'expires_at']
    search_fields = ['user__username', 'description']
    list_per_page = 25

class RewardAdmin(admin.ModelAdmin):
    list_display = ['name', 'points_required', 'discount_percentage', 'product', 'is_active']
    list_filter = ['is_active', 'points_required']
    search_fields = ['name']
    list_per_page = 25

class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percentage', 'valid_from', 'valid_to', 'uses', 'max_uses', 'is_active_link']
    list_filter = ['valid_from', 'valid_to', 'max_uses', 'uses']
    search_fields = ['code']
    list_per_page = 25
    actions = ['toggle_active']

    def is_active_link(self, obj):
        url = reverse('admin:marketing_promocode_change', args=[obj.id], current_app=self.admin_site.name)
        status = "Actif" if obj.is_valid() else "Inactif"
        return format_html('<a href="{}">{}</a>', url, status)
    is_active_link.short_description = 'Statut'

    def toggle_active(self, request, queryset):
        updated = queryset.update(max_uses=0 if queryset.filter(max_uses=0).exists() else 10)
        self.message_user(request, f"{updated} code(s) promo mis à jour.")
    toggle_active.short_description = "Activer/Désactiver les codes sélectionnés"

# Définition du CustomAdminSite
class CustomAdminSite(admin.AdminSite):
    site_header = "Administration e-commerce"
    site_title = "Tableau de bord"

    def get_urls(self):
        from django.urls import path
        from .views import dashboard_view

        urls = [
            path('dashboard/', self.admin_view(dashboard_view), name='dashboard'),
        ]
        return urls + super().get_urls()  # Inclut les URL de l'admin par défaut

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update({
            'dashboard_stats': {
                'total_points': LoyaltyPoint.objects.aggregate(total=Sum('points'))['total'] or 0,
                'total_uses': PromoCode.objects.aggregate(total=Sum('uses'))['total'] or 0,
                'active_codes': PromoCode.objects.filter(valid_to__gte=timezone.now()).count(),
            }
        })
        return super().index(request, extra_context)

# Création de l'instance admin_site
admin_site = CustomAdminSite(name='customadmin')

# Enregistrement des modèles de marketing
admin_site.register(LoyaltyPoint, LoyaltyPointAdmin)
admin_site.register(Reward, RewardAdmin)
admin_site.register(PromoCode, PromoCodeAdmin)