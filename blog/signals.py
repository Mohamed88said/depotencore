from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.db import models

from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps
from django.contrib import admin

@receiver(post_migrate)
def handle_post_migrate(sender, **kwargs):
    if sender.name == 'blog':
        try:
            # Vérifier si le modèle Post existe
            Post = apps.get_model('blog', 'Post')
            Product = apps.get_model('store', 'Product')
            
            # Ajouter dynamiquement le champ products si nécessaire
            if not hasattr(Post, 'products'):
                from django.db import models
                field = models.ManyToManyField(
                    Product,
                    blank=True,
                    related_name='blog_posts',
                    verbose_name='Produits associés'
                )
                field.contribute_to_class(Post, 'products')
            
            # Mise à jour de l'admin seulement si le modèle est enregistré
            if admin.site.is_registered(Post):
                from blog.admin import PostAdmin
                PostAdmin.filter_horizontal = list(getattr(PostAdmin, 'filter_horizontal', [])) + ['products']
                admin.site.unregister(Post)
                admin.site.register(Post, PostAdmin)
                
        except (LookupError, ImportError):
            # Passer silencieusement si les modèles ne sont pas disponibles
            pass

        

@receiver(post_save, sender='blog.Comment')
def send_comment_notification(sender, instance, created, **kwargs):
    if created and not instance.is_approved:
        subject = f"Nouveau commentaire en attente sur {instance.post.title}"
        message = (
            f"Un nouveau commentaire a été soumis sur l'article '{instance.post.title}'.\n\n"
            f"Contenu : {instance.content}\n"
            f"Auteur : {instance.author.username}\n"
            f"Date : {instance.created_at}\n\n"
            f"Approuver ce commentaire dans l'admin : "
            f"{settings.SITE_URL}/admin/blog/comment/{instance.id}/change/\n"
        )
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = settings.ADMIN_EMAILS
        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=True,
        )