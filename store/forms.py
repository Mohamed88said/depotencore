from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import Product, Category, ProductVariant, Review
from captcha.fields import ReCaptchaField
from PIL import Image
import os

class ProductForm(forms.ModelForm):
    """Formulaire principal pour créer/modifier un produit"""
    
    # Champ catégorie personnalisé
    category_name = forms.CharField(
        max_length=100,
        required=False,
        label="Catégorie",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Vêtements, Électronique, Maison...',
            'list': 'categories-list'
        }),
        help_text="Tapez pour rechercher ou créer une nouvelle catégorie"
    )
    
    # Tags
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: mode, tendance, qualité, pas cher...'
        }),
        help_text="Mots-clés séparés par des virgules pour améliorer la recherche"
    )
    
    # Captcha pour éviter le spam
    captcha = ReCaptchaField()

    class Meta:
        model = Product
        fields = [
            'name', 'category_name', 'description', 'short_description',
            'price', 'compare_price', 'stock', 'low_stock_threshold',
            'image1', 'image2', 'image3', 'image4', 'image5',
            'size', 'brand', 'color', 'material', 'condition',
            'weight', 'length', 'width', 'height',
            'tags', 'meta_title', 'meta_description'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de votre produit'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Description détaillée de votre produit...'
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description courte pour les listes de produits'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'compare_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'low_stock_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '5'
            }),
            'image1': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image2': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image3': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image4': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image5': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'size': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'material': forms.TextInput(attrs={'class': 'form-control'}),
            'condition': forms.Select(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'length': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'width': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'meta_title': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pré-remplir la catégorie si le produit existe
        if self.instance.pk and self.instance.category:
            self.fields['category_name'].initial = self.instance.category.name

    def clean_category_name(self):
        category_name = self.cleaned_data.get('category_name')
        if category_name:
            category_name = category_name.strip().title()
            # Créer ou récupérer la catégorie
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={
                    'slug': slugify(category_name),
                    'description': f"Catégorie {category_name}"
                }
            )
            return category
        return None

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise ValidationError("Le prix doit être supérieur à 0.")
        return price

    def clean_compare_price(self):
        compare_price = self.cleaned_data.get('compare_price')
        price = self.cleaned_data.get('price')
        
        if compare_price and price and compare_price <= price:
            raise ValidationError("Le prix de comparaison doit être supérieur au prix de vente.")
        return compare_price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is not None and stock < 0:
            raise ValidationError("Le stock ne peut pas être négatif.")
        return stock

    def clean_image1(self):
        image = self.cleaned_data.get('image1')
        if image:
            return self.validate_image(image)
        return image

    def clean_image2(self):
        image = self.cleaned_data.get('image2')
        if image:
            return self.validate_image(image)
        return image

    def clean_image3(self):
        image = self.cleaned_data.get('image3')
        if image:
            return self.validate_image(image)
        return image

    def clean_image4(self):
        image = self.cleaned_data.get('image4')
        if image:
            return self.validate_image(image)
        return image

    def clean_image5(self):
        image = self.cleaned_data.get('image5')
        if image:
            return self.validate_image(image)
        return image

    def validate_image(self, image):
        """Validation des images"""
        # Taille maximale : 5MB
        if image.size > 5 * 1024 * 1024:
            raise ValidationError("L'image ne doit pas dépasser 5 MB.")
        
        # Formats autorisés
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        ext = os.path.splitext(image.name)[1].lower()
        if ext not in valid_extensions:
            raise ValidationError("Formats autorisés : JPG, JPEG, PNG, WEBP.")
        
        # Vérifier que c'est bien une image
        try:
            img = Image.open(image)
            img.verify()
        except Exception:
            raise ValidationError("Fichier image invalide.")
        
        return image

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Assigner la catégorie
        instance.category = self.cleaned_data.get('category_name')
        
        # Assigner le vendeur
        if self.user:
            instance.seller = self.user
        
        # Définir le statut initial
        if not instance.pk:
            instance.status = 'pending'  # En attente de modération
        
        if commit:
            instance.save()
            
            # Créer la modération si nouveau produit
            if not hasattr(instance, 'moderation'):
                ProductModeration.objects.create(
                    product=instance,
                    status='pending'
                )
        
        return instance

class ProductVariantForm(forms.ModelForm):
    """Formulaire pour les variantes de produit"""
    
    class Meta:
        model = ProductVariant
        fields = ['name', 'sku', 'price', 'stock', 'size', 'color', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'size': forms.Select(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ProductSearchForm(forms.Form):
    """Formulaire de recherche de produits"""
    
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher dans vos produits...'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="Toutes les catégories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'Tous les statuts')] + Product.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    stock_status = forms.ChoiceField(
        choices=[
            ('', 'Tous'),
            ('in_stock', 'En stock'),
            ('low_stock', 'Stock faible'),
            ('out_of_stock', 'Rupture de stock'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class BulkProductActionForm(forms.Form):
    """Formulaire pour les actions en lot sur les produits"""
    
    ACTION_CHOICES = [
        ('', 'Choisir une action'),
        ('activate', 'Activer'),
        ('deactivate', 'Désactiver'),
        ('delete', 'Supprimer'),
        ('update_category', 'Changer de catégorie'),
        ('apply_discount', 'Appliquer une réduction'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Champs conditionnels
    new_category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    discount_percentage = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'})
    )

class ReviewReplyForm(forms.Form):
    """Formulaire pour répondre aux avis"""
    
    reply = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Votre réponse professionnelle...'
        }),
        label="Réponse"
    )

class ProductStatusForm(forms.Form):
    """Formulaire pour changer le statut d'un produit"""
    
    status = forms.ChoiceField(
        choices=Product.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Raison du changement de statut (optionnel)'
        })
    )