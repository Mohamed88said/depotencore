from django import forms
from allauth.account.forms import SignupForm, LoginForm
from .models import CustomUser, Profile, Address
from captcha.fields import ReCaptchaField

class SignUpForm(SignupForm):
    user_type = forms.ChoiceField(choices=CustomUser.USER_TYPE_CHOICES, required=True, label="Rôle", help_text="Choisissez si vous êtes un acheteur ou un vendeur.")
    captcha = ReCaptchaField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'email',
            'id': 'id_email'
        })
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'username',
            'id': 'id_username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'new-password',
            'id': 'id_password1'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'new-password',
            'id': 'id_password2'
        })
        self.fields['user_type'].widget.attrs.update({
            'class': 'form-control',
            'id': 'id_user_type'
        })

    def save(self, request):
        user = super().save(request)
        user.user_type = self.cleaned_data['user_type']
        user.save()
        return user

class LoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['login'].label = "Email ou nom d’utilisateur"
        self.fields['login'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Entrez votre email ou nom d'utilisateur',
            'autocomplete': 'username',
            'id': 'id_login'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Mot de passe',
            'autocomplete': 'current-password',
            'id': 'id_password'
        })

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['address', 'phone', 'profile_picture', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            if picture.size > 5 * 1024 * 1024:  # 5MB max
                raise forms.ValidationError("L'image est trop grande (max 5MB).")
            if not picture.content_type.startswith('image/'):
                raise forms.ValidationError("Le fichier doit être une image.")
        return picture
class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['address_line1', 'address_line2', 'city', 'postal_code', 'country', 'is_default']