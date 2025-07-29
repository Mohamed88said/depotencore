from django import template
from django.forms import BaseForm
from store.models import Favorite

register = template.Library()

@register.filter
def is_favorite(product, user):
    if not user.is_authenticated:
        return False
    return Favorite.objects.filter(user=user, product=product).exists()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def multiply(value, arg):
    """Multiplie deux valeurs numériques."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def as_p(form):
    """Filtre personnalisé pour afficher un formulaire avec as_p"""
    if hasattr(form, 'as_p'):
        return form.as_p()
    return str(form)