from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from decimal import Decimal
from .models import Product, Category, Cart, CartItem, Order, Address, ShippingOption, ProductView, OrderItem
from .forms import ProductForm, CartItemForm
from unittest.mock import patch
import uuid
from PIL import Image
import io
import json
from marketing.models import PromoCode

User = get_user_model()

class StoreModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser_' + str(uuid.uuid4())[:8],
            email='testuser_' + str(uuid.uuid4())[:8] + '@example.com',
            password='testpass',
            user_type='buyer'
        )
        self.seller = User.objects.create_user(
            username='seller_' + str(uuid.uuid4())[:8],
            email='seller_' + str(uuid.uuid4())[:8] + '@example.com',
            password='testpass',
            user_type='seller'
        )
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Test Product',
            description='A test product',
            price=Decimal('100.00'),
            stock=10,
            size='M',
            brand='TestBrand',
            color='Blue',
            material='Cotton'
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.order = Order.objects.create(
            user=self.user,
            total=Decimal('200.00'),
            status='pending',
            seller=self.seller
        )
        self.address = Address.objects.create(
            user=self.user,
            full_name='John Doe',
            street_address='123 Test St',
            postal_code='12345',
            city='Test City',
            country='France',
            is_default=True
        )
        self.shipping_option = ShippingOption.objects.create(
            name='Standard',
            cost=Decimal('5.00'),
            estimated_days=5,
            is_active=True
        )

    def test_product_discounted_price(self):
        """Teste la propriété discounted_price du modèle Product."""
        from .models import Discount
        Discount.objects.create(
            product=self.product,
            percentage=Decimal('10.00'),
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=10),
            is_active=True
        )
        self.assertEqual(self.product.discounted_price, Decimal('90.00'))

    def test_product_is_sold_out(self):
        """Teste la propriété is_sold_out du modèle Product."""
        self.product.stock = 0
        self.assertTrue(self.product.is_sold_out)
        self.product.stock = 10
        self.assertFalse(self.product.is_sold_out)

    def test_category_slug_unique(self):
        """Teste l'unicité du slug dans Category."""
        category = Category(name='Test Category', slug='test-category')
        with self.assertRaises(ValidationError):
            category.full_clean()
            category.save()

    def test_cart_subtotal(self):
        """Teste le calcul du sous-total du panier."""
        self.assertEqual(self.cart_item.subtotal, Decimal('200.00'))  # 2 * 100.00 (sans remise)

    def test_order_total(self):
        """Teste le total de la commande."""
        self.assertEqual(self.order.total, Decimal('200.00'))

    def test_product_view_creation(self):
        """Teste la création d'une ProductView avec une date consciente."""
        product_view = ProductView.objects.create(
            product=self.product,
            view_date=timezone.now(),
            view_count=1
        )
        self.assertEqual(product_view.view_count, 1)
        self.assertTrue(timezone.is_aware(product_view.view_date))

class StoreFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser_' + str(uuid.uuid4())[:8],
            email='testuser_' + str(uuid.uuid4())[:8] + '@example.com',
            password='testpass',
            user_type='buyer'
        )
        self.seller = User.objects.create_user(
            username='seller_' + str(uuid.uuid4())[:8],
            email='seller_' + str(uuid.uuid4())[:8] + '@example.com',
            password='testpass',
            user_type='seller'
        )
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Test Product',
            description='A test product',
            price=Decimal('100.00'),
            stock=10,
            size='M',
            brand='TestBrand',
            color='Blue',
            material='Cotton'
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)

    def test_product_form_valid(self):
        """Teste la validation du formulaire ProductForm."""
        image = Image.new('RGB', (100, 100), color='red')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_file = SimpleUploadedFile("test.jpg", image_io.getvalue(), content_type="image/jpeg")

        data = {
            'name': 'Test Product',
            'description': 'A test product',
            'price': '100.00',
            'stock': 10,
            'category': 'Test Category',
            'size': 'M',
            'brand': 'TestBrand',
            'color': 'Blue',
            'material': 'Cotton',
            'discount_percentage': '10.00',
            'captcha': 'dummy-captcha-response'
        }
        files = {'image1': image_file}

        with patch('captcha.fields.ReCaptchaField.validate', return_value=True):
            form = ProductForm(data=data, files=files)
            self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")

    def test_cart_item_form_valid(self):
        """Teste la validation du formulaire CartItemForm."""
        data = {'quantity': 3}
        form = CartItemForm(data=data, instance=self.cart_item)
        self.assertTrue(form.is_valid())

    def test_cart_item_form_invalid_quantity(self):
        """Teste la validation de quantité négative dans CartItemForm."""
        data = {'quantity': 0}
        form = CartItemForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

class StoreViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser_' + str(uuid.uuid4())[:8],
            email='testuser_' + str(uuid.uuid4())[:8] + '@example.com',
            password='testpass',
            user_type='buyer'
        )
        self.seller = User.objects.create_user(
            username='seller_' + str(uuid.uuid4())[:8],
            email='seller_' + str(uuid.uuid4())[:8] + '@example.com',
            password='testpass',
            user_type='seller'
        )
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Test Product',
            description='A test product',
            price=Decimal('100.00'),
            stock=10,
            size='M',
            brand='TestBrand',
            color='Blue',
            material='Cotton'
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.address = Address.objects.create(
            user=self.user,
            full_name='John Doe',
            street_address='123 Test St',
            postal_code='12345',
            city='Test City',
            country='France',
            is_default=True
        )
        self.shipping_option = ShippingOption.objects.create(
            name='Standard',
            cost=Decimal('5.00'),
            estimated_days=5,
            is_active=True
        )
        self.order = Order.objects.create(
            user=self.user,
            total=Decimal('205.00'),
            status='pending',
            seller=self.seller,
            shipping_address=self.address,
            shipping_option=self.shipping_option
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal('100.00'),
            seller=self.seller
        )
        self.promo_code = PromoCode.objects.create(
            code='TEST10',
            discount_percentage=Decimal('10.00'),
            valid_from=timezone.now(),
            valid_to=timezone.now() + timezone.timedelta(days=10),
            max_uses=100,
            uses=0
        )
        self.promo_code.users.add(self.user)  # Ajouté ici pour garantir que l'utilisateur est associé

    def test_product_list_view(self):
        """Teste la vue product_list."""
        response = self.client.get(reverse('store:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/product_list.html')
        self.assertIn('page_obj', response.context)

    def test_product_detail_view(self):
        """Teste la vue product_detail."""
        response = self.client.get(reverse('store:product_detail', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/product_detail.html')
        self.assertEqual(response.context['product'], self.product)

    def test_cart_view(self):
        """Teste la vue cart."""
        self.client.login(username=self.user.username, password='testpass')
        response = self.client.get(reverse('store:cart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/cart.html')
        self.assertIn('cart_items', response.context)

    def test_add_to_cart_authenticated(self):
        """Teste l'ajout au panier pour un utilisateur authentifié."""
        self.client.login(username=self.user.username, password='testpass')
        response = self.client.get(reverse('store:add_to_cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CartItem.objects.filter(cart__user=self.user, product=self.product).exists())

    def test_update_cart_view(self):
        """Teste la vue update_cart."""
        self.client.login(username=self.user.username, password='testpass')
        data = {'quantity': 3}
        response = self.client.post(reverse('store:update_cart', args=[self.cart_item.id]), data)
        self.assertEqual(response.status_code, 302)
        self.cart_item.refresh_from_db()
        self.assertEqual(self.cart_item.quantity, 3)

    def test_remove_from_cart(self):
        """Teste la suppression d'un article du panier."""
        self.client.login(username=self.user.username, password='testpass')
        response = self.client.get(reverse('store:remove_from_cart', args=[self.cart_item.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CartItem.objects.filter(id=self.cart_item.id).exists())

    def test_checkout_unauthenticated(self):
        """Teste l'accès à la page checkout sans authentification."""
        response = self.client.get(reverse('store:checkout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_checkout_authenticated(self):
        """Teste l'accès à la page checkout avec authentification."""
        self.client.login(username=self.user.username, password='testpass')
        response = self.client.get(reverse('store:checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/checkout.html')

    def test_product_create_view_seller(self):
        """Teste la vue product_create pour un vendeur."""
        self.client.login(username=self.seller.username, password='testpass')
        response = self.client.get(reverse('store:product_create'))
        self.assertEqual(response.status_code, 200, msg=f"Response content: {response.content.decode()}")
        self.assertTemplateUsed(response, 'store/product_form.html')

    def test_mark_as_sold_view(self):
        """Teste la vue mark_as_sold."""
        self.client.login(username=self.seller.username, password='testpass')
        response = self.client.get(reverse('store:mark_as_sold', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/confirm_sold.html')

    @patch('store.views.stripe.PaymentIntent.create')
    @patch('store.views.stripe.Customer.list')
    @patch('store.views.stripe.Customer.create')
    @patch('store.views.stripe.PaymentMethod.attach')
    @patch('store.views.stripe.Charge.list')
    def test_process_payment_cod(self):
        """Teste le traitement du paiement à la livraison."""
        self.client.login(username=self.user.username, password='testpass')
        data = {
            'payment_method': 'cod',
            'address': self.address.id,
            'shipping_option': self.shipping_option.id
        }
        response = self.client.post(reverse('store:process_payment'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.filter(user=self.user).exists())

    def test_product_update_view_seller(self):
        """Teste la vue product_update pour un vendeur."""
        self.client.login(username=self.seller.username, password='testpass')
        data = {
            'name': 'Updated Product',
            'description': 'An updated product',
            'price': '150.00',
            'stock': 5,
            'category': 'Test Category',
            'size': 'L',
            'brand': 'NewBrand',
            'color': 'Red',
            'material': 'Wool',
            'discount_percentage': '10.00',
            'captcha': 'dummy-captcha-response'
        }
        image = Image.new('RGB', (100, 100), color='red')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_file = SimpleUploadedFile("test.jpg", image_io.getvalue(), content_type="image/jpeg")
        files = {'image1': image_file}
        with patch('captcha.fields.ReCaptchaField.validate', return_value=True):
            response = self.client.post(reverse('store:product_update', args=[self.product.id]), data, files=files)
            self.assertEqual(response.status_code, 302)
            self.product.refresh_from_db()
            self.assertEqual(self.product.name, 'Updated Product')
            self.assertEqual(self.product.price, Decimal('150.00'))

    def test_order_history_view(self):
        """Teste la vue order_history."""
        self.client.login(username=self.user.username, password='testpass')
        response = self.client.get(reverse('store:order_history'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/order_history.html')
        self.assertIn('orders', response.context)

    def test_order_detail_view(self):
        """Teste la vue order_detail."""
        self.client.login(username=self.user.username, password='testpass')
        response = self.client.get(reverse('store:order_detail', args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/order_detail.html')
        self.assertEqual(response.context['order'], self.order)

    def test_payment_success_view(self):
        """Teste la vue payment_success."""
        self.client.login(username=self.user.username, password='testpass')
        response = self.client.get(reverse('store:payment_success', args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/payment_success.html')

    def test_apply_promo_code_valid(self):
        """Teste l'application d'un code promo valide."""
        self.client.login(username=self.user.username, password='testpass')
        # Vérifier que le panier contient des articles
        self.assertTrue(self.cart.items.exists(), msg="Le panier est vide")
        # Vérifier que le code promo est valide
        self.assertTrue(self.promo_code.is_valid(self.user), msg=f"Promo code invalid: valid_from={self.promo_code.valid_from}, valid_to={self.promo_code.valid_to}, uses={self.promo_code.uses}, max_uses={self.promo_code.max_uses}")
        data = {'promo_code': 'TEST10'}
        response = self.client.post(reverse('store:apply_promo_code'), json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200, msg=f"Response content: {response.content.decode()}")
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'], msg=f"Response data: {response_data}")
        self.assertEqual(float(response_data['discount_amount']), 20.0, msg=f"Response data: {response_data}")  # 200.00 * 10%
        self.assertEqual(float(response_data['new_total']), 185.0, msg=f"Response data: {response_data}")  # 200.00 + 5.00 - 20.00

    def test_apply_promo_code_invalid(self):
        """Teste l'application d'un code promo invalide."""
        self.client.login(username=self.user.username, password='testpass')
        data = {'promo_code': 'INVALID'}
        response = self.client.post(reverse('store:apply_promo_code'), json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['message'], 'Code promo introuvable.')

    @patch('requests.get')
    def test_geocode_view(self, mock_get):
        """Teste la vue geocode."""
        self.client.login(username=self.user.username, password='testpass')
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'address': {
                'road': 'Test Road',
                'city': 'Test City',
                'postcode': '12345',
                'country': 'France'
            }
        }
        data = {'latitude': 9.6412, 'longitude': -13.5783}
        response = self.client.post(reverse('store:geocode'), json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['address']['street_address'], 'Test Road')