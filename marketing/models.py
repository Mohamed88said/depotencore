from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

User = get_user_model()

class LoyaltyPoint(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loyalty_points')
    points = models.PositiveIntegerField(default=0)
    earned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.points} points for {self.user.username} ({self.earned_at})"

    class Meta:
        ordering = ['-earned_at']

class Reward(models.Model):
    name = models.CharField(max_length=100)
    points_required = models.PositiveIntegerField()
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    product = models.ForeignKey('store.Product', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.points_required} points)"

    class Meta:
        ordering = ['points_required']

class PromoCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(default= timezone.now() + timedelta(days=30))  # Ajusté
    max_uses = models.PositiveIntegerField(default=0)
    uses = models.PositiveIntegerField(default=0)
    users = models.ManyToManyField(User, blank=True, related_name='promo_codes')

    def is_valid(self, user=None):
        now = timezone.now()
        return self.valid_from <= now <= self.valid_to and self.uses < self.max_uses and \
               (not self.users.exists() or (user and self.users.filter(id=user.id).exists()))

    def apply(self, total):
        if self.is_valid():
            discount = total * (self.discount_percentage / Decimal('100'))
            self.uses += 1
            self.save()
            return discount
        return Decimal('0')

    def __str__(self):
        return f"{self.code} ({self.discount_percentage}%)"