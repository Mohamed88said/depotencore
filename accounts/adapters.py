from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse
from django.shortcuts import redirect

class CustomAccountAdapter(DefaultAccountAdapter):
    
    def get_login_redirect_url(self, request):
        """Redirection après connexion selon le type d'utilisateur"""
        user = request.user
        
        if user.user_type == 'seller':
            return reverse('vendor:dashboard')
        elif user.user_type == 'delivery':
            return reverse('delivery:dashboard')
        else:
            return reverse('store:home')
    
    def get_signup_redirect_url(self, request):
        """Redirection après inscription"""
        return self.get_login_redirect_url(request)
    
    def save_user(self, request, user, form, commit=True):
        """Sauvegarde personnalisée de l'utilisateur"""
        user = super().save_user(request, user, form, commit=False)
        
        # Le type d'utilisateur sera défini dans les formulaires personnalisés
        if commit:
            user.save()
        return user