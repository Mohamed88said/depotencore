from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import (
    Product, Order, Category, Review, CartItem, Address, ShippingOption, SellerProfile, ProductRequest,
    GuineaRegion, GuineaPrefecture, GuineaQuartier, GuineaAddress, UserLocation, DeliveryLocation
)
from admin_panel.models import Report
from captcha.fields import ReCaptchaField

class DiscountForm(forms.Form):
    """Formulaire pour appliquer une réduction"""
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Produits"
    )
    percentage = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0.01,
        max_value=100,
        label="Pourcentage de réduction (%)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    start_date = forms.DateTimeField(
        label="Date de début",
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
    )
    end_date = forms.DateTimeField(
        label="Date de fin",
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
    )
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['products'].queryset = Product.objects.filter(seller=user, is_sold=False)
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise ValidationError("La date de fin doit être postérieure à la date de début.")
        
        return cleaned_data

class MessageForm(forms.Form):
    """Formulaire pour envoyer un message"""
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Tapez votre message...'
        }),
        label="Message"
    )

class ReviewReplyForm(forms.Form):
    """Formulaire pour répondre à un avis"""
    reply = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Votre réponse...'
        }),
        label="Réponse"
    )

class ProductRequestResponseForm(forms.Form):
    """Formulaire pour répondre à une demande de produit"""
    response = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Votre réponse au client...'
        }),
        label="Réponse"
    )
    restock_quantity = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantité à ajouter au stock'
        }),
        label="Restockage (optionnel)"
    )

class SellerRatingForm(forms.Form):
    """Formulaire pour noter un vendeur"""
    rating = forms.ChoiceField(
        choices=[(i, i) for i in range(1, 6)],
        widget=forms.RadioSelect,
        label="Note"
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Commentaire (optionnel)'
        }),
        label="Commentaire"
    )

class SellerProfileForm(forms.ModelForm):
    """Formulaire pour le profil vendeur"""
    class Meta:
        model = SellerProfile
        fields = ['first_name', 'last_name', 'description', 'business_name', 'business_address', 'contact_phone', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ProductForm(forms.ModelForm):
    category = forms.CharField(max_length=100, required=False, label="Catégorie")
    captcha = ReCaptchaField()

    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'price', 'stock', 'image1', 'image2', 'image3', 'size', 'brand', 'color', 'material']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'id': 'id_description'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'id': 'id_price'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'id': 'id_stock'}),
            'image1': forms.ClearableFileInput(attrs={'class': 'form-control', 'id': 'id_image1'}),
            'image2': forms.ClearableFileInput(attrs={'class': 'form-control', 'id': 'id_image2'}),
            'image3': forms.ClearableFileInput(attrs={'class': 'form-control', 'id': 'id_image3'}),
            'size': forms.Select(attrs={'class': 'form-control', 'id': 'id_size'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_brand'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_color'}),
            'material': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_material'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.category:
            self.fields['category'].initial = self.instance.category.name

    def clean_category(self):
        category_name = self.cleaned_data.get('category')
        if category_name:
            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={'slug': category_name.lower().replace(' ', '-')})
            return category
        return None

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError("Le prix doit être supérieur à 0.")
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is not None and stock < 0:
            raise forms.ValidationError("Le stock ne peut pas être négatif.")
        return stock

    def save(self, **kwargs):
        commit = kwargs.pop('commit', True)
        instance = super().save(commit=False)
        instance.category = self.cleaned_data.get('category')
        if commit:
            instance.save()
        return instance

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['full_name', 'street_address', 'city', 'postal_code', 'country', 'phone_number', 'is_default']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_full_name', 'autocomplete': 'name'}),
            'street_address': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_street_address', 'autocomplete': 'street-address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_city', 'autocomplete': 'address-level2'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_postal_code', 'autocomplete': 'postal-code'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_country', 'autocomplete': 'country', 'value': 'Guinée'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_phone_number', 'autocomplete': 'tel'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_is_default'}),
        }

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CartItemForm(forms.ModelForm):
    class Meta:
        model = CartItem
        fields = ['quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1, 'class': 'form-control'})
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity < 1:
            raise forms.ValidationError("La quantité doit être supérieure ou égale à 1.")
        return quantity

class ProductRequestForm(forms.ModelForm):
    email = forms.EmailField(
        required=False,
        help_text="Entrez votre email si vous n'êtes pas connecté.",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Votre email'})
    )
    captcha = ReCaptchaField()

    class Meta:
        model = ProductRequest
        fields = ['email', 'message', 'desired_quantity', 'desired_date']
        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'desired_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'desired_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and user.is_authenticated:
            self.fields['email'].widget = forms.HiddenInput()
            self.fields['email'].required = False
        else:
            self.fields['email'].required = True

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason', 'description']
        widgets = {
            'reason': forms.Select(choices=[
                ('inappropriate_content', 'Contenu inapproprié'),
                ('fraud', 'Fraude'),
                ('spam', 'Spam'),
                ('other', 'Autre'),
            ], attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Décrivez le problème en détail...', 'class': 'form-control'}),
        }

class CheckoutForm(forms.Form):
    # Mode de livraison
    delivery_mode = forms.ChoiceField(
        choices=[
            ('home', 'Livraison à domicile'),
            ('pickup', 'Retrait en boutique')
        ],
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
        initial='home',
        label="Mode de livraison"
    )
    
    # Mode de paiement futur
    preferred_payment_method = forms.ChoiceField(
        choices=[
            ('cash', 'Espèces'),
            ('card', 'Carte bancaire'),
            ('paypal', 'PayPal')
        ],
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
        initial='cash',
        label="Comment souhaitez-vous payer à la livraison ?"
    )
    
    # Qui paie la commission de livraison
    commission_payer = forms.ChoiceField(
        choices=[
            ('customer', 'Je paie la commission de livraison'),
            ('vendor', 'Le vendeur paie la commission')
        ],
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
        initial='customer',
        label="Commission de livraison"
    )
    
    # Mode d'adresse
    address_mode = forms.ChoiceField(
        choices=[('existing', 'Adresse existante'), ('new', 'Nouvelle adresse')],
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
        initial='existing'
    )
    
    # Adresse existante
    address = forms.ModelChoiceField(
        queryset=Address.objects.none(),
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    # Nouvelle adresse
    full_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'})
    )
    street_address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'street-address'})
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'address-level2'})
    )
    postal_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'postal-code'})
    )
    country = forms.CharField(
        max_length=100,
        initial='Guinée',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'country'})
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'tel'})
    )
    
    # Géolocalisation
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    location_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
    
    # Instructions spéciales pour la livraison
    special_instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3,
            'placeholder': 'Instructions spéciales pour le livreur (ex: sonner 2 fois, appartement au 2ème étage...)'
        }),
        label="Instructions spéciales"
    )
    
    # Options de livraison et paiement
    shipping_option = forms.ModelChoiceField(
        queryset=ShippingOption.objects.filter(is_active=True),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['address'].queryset = Address.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()
        delivery_mode = cleaned_data.get('delivery_mode')
        address_mode = cleaned_data.get('address_mode')
        
        # Validation adresse seulement si livraison à domicile
        if delivery_mode == 'home':
            if address_mode == 'existing':
                if not cleaned_data.get('address'):
                    raise forms.ValidationError("Veuillez sélectionner une adresse pour la livraison.")
            else:
                required_fields = ['full_name', 'street_address', 'city', 'postal_code', 'country']
                for field in required_fields:
                    if not cleaned_data.get(field):
                        raise forms.ValidationError(f"Le champ {field} est requis pour une nouvelle adresse.")
        
        return cleaned_data