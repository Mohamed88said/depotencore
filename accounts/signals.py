
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, Profile

@receiver(post_save, sender=CustomUser)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        
        # Créer un profil livreur si c'est un livreur
        if instance.user_type == 'delivery':
            from store.models import DeliveryProfile
            DeliveryProfile.objects.create(user=instance)
