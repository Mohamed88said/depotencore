from django import forms
from store.models import Category, Product
from returns.models import ReturnRequest

class StatisticsFilterForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label="Date de début"
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label="Date de fin"
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label="Catégorie",
        empty_label="Toutes les catégories"
    )

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'stock', 'category', 'image1', 'image2', 'image3', 'size', 'brand', 'color', 'material']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'min': '0', 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'image1': forms.FileInput(attrs={'class': 'form-control'}),
            'image2': forms.FileInput(attrs={'class': 'form-control'}),
            'image3': forms.FileInput(attrs={'class': 'form-control'}),
            'size': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'material': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Nom du produit',
            'description': 'Description',
            'price': 'Prix (€)',
            'stock': 'Stock',
            'category': 'Catégorie',
            'image1': 'Image principale',
            'image2': 'Image secondaire',
            'image3': 'Image supplémentaire',
            'size': 'Taille',
            'brand': 'Marque',
            'color': 'Couleur',
            'material': 'Matériau',
        }

    def clean_discount_percentage(self):
        discount = self.cleaned_data.get('discount_percentage')
        if discount is not None and (discount < 0 or discount > 100):
            raise forms.ValidationError("Le pourcentage de réduction doit être entre 0 et 100.")
        return discount

class ReturnRequestForm(forms.ModelForm):
    class Meta:
        model = ReturnRequest
        fields = ['reason', 'image']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Expliquez la raison du retour'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'reason': 'Raison du retour',
            'image': 'Photo du produit retourné (optionnel)',
        }