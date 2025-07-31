from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from unittest.mock import patch
from .forms import ProductForm, CheckoutForm, AddressForm, ReviewForm
from .models import Category, Product, Address, ShippingOption

User = get_user_model()

class ProductFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='seller'
        )

    @patch('captcha.fields.ReCaptchaField.validate')
    def test_product_form_valid(self, mock_captcha):
        """Test formulaire produit valide"""
        mock_captcha.return_value = True
        
        data = {
            'name': 'Test Product',
            'description': 'Test description',
            'price': '100.00',
            'stock': 10,
            'category': 'Test Category',
            'size': 'M',
            'brand': 'Test Brand',
            'color': 'Blue',
            'material': 'Cotton',
            'captcha': 'dummy-captcha'
        }
        
        form = ProductForm(data=data)
        self.assertTrue(form.is_valid())

    def test_product_form_invalid_price(self):
        """Test formulaire avec prix invalide"""
        data = {
            'name': 'Test Product',
            'description': 'Test description',
            'price': '-10.00',  # Prix négatif
            'stock': 10,
            'category': 'Test Category',
            'captcha': 'dummy-captcha'
        }
        
        with patch('captcha.fields.ReCaptchaField.validate', return_value=True):
            form = ProductForm(data=data)
            self.assertFalse(form.is_valid())
            self.assertIn('price', form.errors)

class CheckoutFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='buyer'
        )
        self.address = Address.objects.create(
            user=self.user,
            full_name='Test User',
            street_address='123 Test St',
            city='Test City',
            postal_code='12345',
            country='Test Country'
        )
        self.shipping_option = ShippingOption.objects.create(
            name='Standard',
            cost=Decimal('5.00'),
            estimated_days=3,
            is_active=True
        )

    def test_checkout_form_existing_address(self):
        """Test formulaire checkout avec adresse existante"""
        data = {
            'delivery_mode': 'home',
            'preferred_payment_method': 'cash',
            'commission_payer': 'customer',
            'address_mode': 'existing',
            'address': self.address.id,
            'shipping_option': self.shipping_option.id
        }
        
        form = CheckoutForm(data=data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_checkout_form_new_address(self):
        """Test formulaire checkout avec nouvelle adresse"""
        data = {
            'delivery_mode': 'home',
            'preferred_payment_method': 'cash',
            'commission_payer': 'customer',
            'address_mode': 'new',
            'full_name': 'New User',
            'street_address': '456 New St',
            'city': 'New City',
            'postal_code': '67890',
            'country': 'New Country',
            'shipping_option': self.shipping_option.id
        }
        
        form = CheckoutForm(data=data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_checkout_form_pickup_mode(self):
        """Test formulaire checkout mode retrait"""
        data = {
            'delivery_mode': 'pickup',
            'preferred_payment_method': 'cash',
            'commission_payer': 'vendor',
            'address_mode': 'existing',
            'shipping_option': self.shipping_option.id
        }
        
        form = CheckoutForm(data=data, user=self.user)
        self.assertTrue(form.is_valid())

class AddressFormTest(TestCase):
    def test_address_form_valid(self):
        """Test formulaire adresse valide"""
        data = {
            'full_name': 'Test User',
            'street_address': '123 Test St',
            'city': 'Test City',
            'postal_code': '12345',
            'country': 'Test Country',
            'phone_number': '+1234567890'
        }
        
        form = AddressForm(data=data)
        self.assertTrue(form.is_valid())

    def test_address_form_required_fields(self):
        """Test champs obligatoires formulaire adresse"""
        data = {
            'full_name': '',  # Champ obligatoire vide
            'street_address': '123 Test St',
            'city': 'Test City',
            'postal_code': '12345',
            'country': 'Test Country'
        }
        
        form = AddressForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('full_name', form.errors)

class ReviewFormTest(TestCase):
    def test_review_form_valid(self):
        """Test formulaire avis valide"""
        data = {
            'rating': 5,
            'comment': 'Excellent product!'
        }
        
        form = ReviewForm(data=data)
        self.assertTrue(form.is_valid())

    def test_review_form_invalid_rating(self):
        """Test formulaire avis avec note invalide"""
        data = {
            'rating': 6,  # Note > 5
            'comment': 'Good product'
        }
        
        form = ReviewForm(data=data)
        self.assertFalse(form.is_valid())