from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import CustomUser, Profile, SellerProfile

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """Créer automatiquement un profil pour chaque utilisateur"""
    if created:
        Profile.objects.create(user=instance)
        
        # Créer un profil vendeur si c'est un vendeur
        if instance.user_type == 'seller':
            SellerProfile.objects.create(
                user=instance,
                business_name=f"Boutique de {instance.username}"
            )
            # Marquer la date de début en tant que vendeur
            instance.seller_since = timezone.now()
            instance.save(update_fields=['seller_since'])
        
        # Créer un profil livreur si c'est un livreur
        elif instance.user_type == 'delivery':
            from store.models import DeliveryProfile
            DeliveryProfile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    """Sauvegarder le profil quand l'utilisateur est sauvegardé"""
    if hasattr(instance, 'profile'):
        instance.profile.save()