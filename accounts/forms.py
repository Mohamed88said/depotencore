from django import forms
from allauth.account.forms import SignupForm, LoginForm
from .models import CustomUser, Profile, SellerProfile
from captcha.fields import ReCaptchaField
from django.core.exceptions import ValidationError

class VendorSignUpForm(SignupForm):
    """Formulaire d'inscription spécifique aux vendeurs"""
    
    # Informations personnelles
    first_name = forms.CharField(
        max_length=100,
        required=True,
        label="Prénom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre prénom'
        })
    )
    
    last_name = forms.CharField(
        max_length=100,
        required=True,
        label="Nom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre nom'
        })
    )
    
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        label="Téléphone",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+224 XX XX XX XX'
        })
    )
    
    # Informations business
    business_name = forms.CharField(
        max_length=200,
        required=True,
        label="Nom de votre entreprise/boutique",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Boutique Mamadou, Shop Aminata...'
        })
    )
    
    business_description = forms.CharField(
        required=True,
        label="Description de votre activité",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Décrivez ce que vous vendez (vêtements, électronique, artisanat...)'
        })
    )
    
    business_address = forms.CharField(
        required=True,
        label="Adresse de votre boutique",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Adresse complète de votre boutique'
        })
    )
    
    # Type de vendeur
    VENDOR_TYPE_CHOICES = [
        ('individual', 'Vendeur individuel'),
        ('small_business', 'Petite entreprise'),
        ('company', 'Entreprise'),
    ]
    
    vendor_type = forms.ChoiceField(
        choices=VENDOR_TYPE_CHOICES,
        required=True,
        label="Type de vendeur",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Acceptation des conditions
    accept_terms = forms.BooleanField(
        required=True,
        label="J'accepte les conditions générales de vente",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    accept_vendor_terms = forms.BooleanField(
        required=True,
        label="J'accepte les conditions spécifiques aux vendeurs",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Captcha
    captcha = ReCaptchaField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personnaliser les champs hérités
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'votre.email@exemple.com'
        })
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nom d\'utilisateur unique'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Mot de passe sécurisé'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmez votre mot de passe'
        })

    def clean_business_name(self):
        business_name = self.cleaned_data.get('business_name')
        if business_name:
            # Vérifier l'unicité du nom de boutique
            if SellerProfile.objects.filter(business_name__iexact=business_name).exists():
                raise ValidationError("Ce nom de boutique est déjà utilisé.")
        return business_name

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Validation basique du format guinéen
            if not phone.startswith('+224') and not phone.startswith('224'):
                if not phone.startswith('6') and not phone.startswith('7'):
                    raise ValidationError("Numéro de téléphone guinéen invalide.")
        return phone

    def save(self, request):
        # Créer l'utilisateur avec le type vendeur
        user = super().save(request)
        user.user_type = 'seller'
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        
        # Le profil vendeur sera créé automatiquement par le signal
        # Mais on met à jour avec les données du formulaire
        seller_profile = user.seller_profile
        seller_profile.first_name = self.cleaned_data['first_name']
        seller_profile.last_name = self.cleaned_data['last_name']
        seller_profile.business_name = self.cleaned_data['business_name']
        seller_profile.business_description = self.cleaned_data['business_description']
        seller_profile.business_address = self.cleaned_data['business_address']
        seller_profile.business_phone = self.cleaned_data['phone_number']
        seller_profile.vendor_type = self.cleaned_data['vendor_type']
        seller_profile.save()
        
        return user

class BuyerSignUpForm(SignupForm):
    """Formulaire d'inscription pour les acheteurs"""
    
    first_name = forms.CharField(
        max_length=100,
        required=False,
        label="Prénom (optionnel)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre prénom'
        })
    )
    
    last_name = forms.CharField(
        max_length=100,
        required=False,
        label="Nom (optionnel)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre nom'
        })
    )
    
    captcha = ReCaptchaField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'votre.email@exemple.com'
        })
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nom d\'utilisateur'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmez le mot de passe'
        })

    def save(self, request):
        user = super().save(request)
        user.user_type = 'buyer'
        if self.cleaned_data.get('first_name'):
            user.first_name = self.cleaned_data['first_name']
        if self.cleaned_data.get('last_name'):
            user.last_name = self.cleaned_data['last_name']
        user.save()
        return user

class CustomLoginForm(LoginForm):
    """Formulaire de connexion personnalisé"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['login'].label = "Email ou nom d'utilisateur"
        self.fields['login'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Entrez votre email ou nom d\'utilisateur'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Votre mot de passe'
        })

class SellerProfileForm(forms.ModelForm):
    """Formulaire pour modifier le profil vendeur"""
    
    class Meta:
        model = SellerProfile
        fields = [
            'first_name', 'last_name', 'business_name', 'business_description',
            'business_address', 'business_phone', 'business_email',
            'profile_picture', 'business_logo', 'return_policy', 'shipping_policy'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'business_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'business_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'business_logo': forms.FileInput(attrs={'class': 'form-control'}),
            'return_policy': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'shipping_policy': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class ProfileForm(forms.ModelForm):
    """Formulaire pour le profil général"""
    
    class Meta:
        model = Profile
        fields = ['address', 'phone', 'profile_picture', 'description']
        widgets = {
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }