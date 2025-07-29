from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import Profile, Address, CustomUser
from accounts.forms import SignUpForm, AddressForm, ProfileForm
from django.core import mail
from unittest.mock import patch

CustomUser = get_user_model()

class CustomUserModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            user_type='buyer'
        )

    def test_user_creation(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.user_type, 'buyer')
        self.assertTrue(self.user.check_password('password123'))

    def test_profile_auto_creation(self):
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            user_type='buyer'
        )
        self.profile = self.user.profile

    def test_profile_str(self):
        self.assertEqual(str(self.profile), f"Profil de {self.user.username}")

    def test_profile_picture_upload(self):
        image = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")
        self.profile.profile_picture = image
        self.profile.save()
        self.assertTrue(self.profile.profile_picture.name.startswith('profile_pics/test'))

class AddressModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            user_type='buyer'
        )
        self.profile = self.user.profile
        self.address = Address.objects.create(
            profile=self.profile,
            address_line1='123 Rue Test',
            city='Paris',
            postal_code='75001',
            country='France',
            is_default=True
        )

    def test_address_str(self):
        self.assertEqual(str(self.address), '123 Rue Test, Paris, France')

    def test_default_address(self):
        address2 = Address.objects.create(
            profile=self.profile,
            address_line1='456 Rue Test',
            city='Lyon',
            postal_code='69001',
            country='France',
            is_default=True
        )
        self.address.refresh_from_db()
        self.assertFalse(self.address.is_default)
        self.assertTrue(address2.is_default)

class SignUpFormTest(TestCase):
    @patch('captcha.fields.ReCaptchaField.validate')
    def test_valid_signup_form(self, mock_captcha):
        mock_captcha.return_value = True
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
            'user_type': 'buyer',
            'captcha': 'dummy-captcha'
        }
        form = SignUpForm(data)
        self.assertTrue(form.is_valid())

    def test_invalid_email(self):
        data = {
            'username': 'newuser',
            'email': 'invalid-email',
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
            'user_type': 'buyer',
            'captcha': 'dummy-captcha'
        }
        form = SignUpForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )

    def test_login_success(self):
        response = self.client.post(reverse('account_login'), {
            'login': 'test@example.com',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:profile'))

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('account_login'), {
            'login': 'test@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "L’adresse e-mail ou le mot de passe sont incorrects.")

class ProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.client.login(username='testuser', password='password123')

    def test_profile_page_access(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')

    def test_profile_update(self):
        response = self.client.post(reverse('accounts:profile'), {
            'address': '123 Rue Test',
            'phone': '0123456789',
            'description': 'Test description'
        })
        if response.status_code != 302:
            print("Response context:", response.context)
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.address, '123 Rue Test')

class SellerProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.buyer = CustomUser.objects.create_user(
            username='buyeruser',
            email='buyer@example.com',
            password='password123',
            user_type='buyer'
        )
        self.seller = CustomUser.objects.create_user(
            username='selleruser',
            email='seller@example.com',
            password='password123',
            user_type='seller'
        )
        self.client.login(username='buyeruser', password='password123')

    def test_seller_profile_access(self):
        response = self.client.get(reverse('accounts:seller_profile', args=['selleruser']))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/seller_profile.html')

    def test_non_seller_redirect(self):
        response = self.client.get(reverse('accounts:seller_profile', args=['buyeruser']))
        self.assertRedirects(response, reverse('accounts:profile'))