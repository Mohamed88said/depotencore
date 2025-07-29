from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from store.models import Cart, CartItem, Product, Address, ShippingOption, Order
from marketing.models import LoyaltyPoint, PromoCode
from accounts.models import CustomUser
from django.utils import timezone
from datetime import timedelta
import json

class MarketingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='testpass',
            user_type='buyer'
        )
        self.client.login(username='testuser', password='testpass')
        self.product = Product.objects.create(
            name='Test Product',
            price=50.00,
            stock=10,
            seller=self.user
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1
        )
        self.address = Address.objects.create(
            user=self.user,
            full_name='Test User',
            street_address='123 Test St',
            postal_code='12345',
            city='Test City',
            country='France',
            is_default=True
        )
        self.shipping_option = ShippingOption.objects.create(
            name='Standard Shipping',
            cost=5.00,
            is_active=True,
            estimated_days=2
        )
        self.promo_code = PromoCode.objects.create(
            code='SAVE10',
            discount_percentage=10.00,
            valid_from=timezone.now(),
            valid_to=timezone.now() + timedelta(days=7),
            max_uses=10
        )

    def test_loyalty_point_creation(self):
        """Teste la création d'un objet LoyaltyPoint."""
        LoyaltyPoint.objects.create(
            user=self.user,
            points=5,
            description='Test points'
        )
        self.assertEqual(LoyaltyPoint.objects.count(), 1)
        point = LoyaltyPoint.objects.first()
        self.assertEqual(point.points, 5)
        self.assertEqual(point.user.id, self.user.id)

    def test_promo_code_validation(self):
        """Teste la validation d'un code promo."""
        self.assertTrue(self.promo_code.is_valid(self.user))
        expired_code = PromoCode.objects.create(
            code='EXPIRED',
            discount_percentage=10.00,
            valid_from=timezone.now() - timedelta(days=10),
            valid_to=timezone.now() - timedelta(days=1),
            max_uses=10
        )
        self.assertFalse(expired_code.is_valid(self.user))

    def test_apply_promo_code_view(self):
        """Teste la vue apply_promo_code."""
        response = self.client.post(
            reverse('store:apply_promo_code'),
            json.dumps({'promo_code': 'SAVE10'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.client.session.get('_csrftoken')
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['discount_amount'], 5.0)  # 10% de 50€
        self.assertEqual(data['new_total'], 50.0 + 5.0 - 5.0)  # subtotal + shipping - discount

        # Teste un code invalide
        response = self.client.post(
            reverse('store:apply_promo_code'),
            json.dumps({'promo_code': 'INVALID'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.client.session.get('_csrftoken')
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Code promo introuvable.')

    def test_process_payment_with_promo_and_points(self):
        """Teste process_payment avec un code promo et des points de fidélité."""
        # Appliquer le code promo
        response = self.client.post(
            reverse('store:apply_promo_code'),
            json.dumps({'promo_code': 'SAVE10'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.client.session.get('_csrftoken')
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        # Passer la commande
        response = self.client.post(
            reverse('store:process_payment'),
            {
                'address': str(self.address.id),
                'shipping_option': str(self.shipping_option.id),
                'payment_method': 'cod',
                'payment_method_id': 'cod',
            }
        )
        self.assertEqual(response.status_code, 302)  # Redirection vers payment_success
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.total, Decimal('50.00'))  # 50 + 5 - 5
        self.assertEqual(LoyaltyPoint.objects.count(), 1)
        point = LoyaltyPoint.objects.first()
        self.assertEqual(point.points, 5)  # 50 // 10 = 5 points
        # Recharger l'instance promo_code pour refléter les changements
        self.promo_code.refresh_from_db()
        self.assertEqual(self.promo_code.uses, 1)