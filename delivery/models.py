from django.db import models
from django.conf import settings
from store.models import Order  # Assurez-vous que Order existe dans store/models.py
from django.core.files.storage import FileSystemStorage

class Location(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_locations')
    photo = models.ImageField(upload_to='delivery/photos/', null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    description = models.TextField(max_length=500, help_text="Ex: En face de la mosquée Diaouné")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.description[:50]}"

class Delivery(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='deliveries')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    delivery_person = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='delivery_assignments'  # Correction du related_name
    )
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('DELIVERED', 'Delivered'),
    ], default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Delivery for Order {self.order.id} - {self.status}"