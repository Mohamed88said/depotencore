from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from .models import (
    Product, Category, Cart, CartItem, Order, OrderItem, Address, 
    ShippingOption, Discount, QRDeliveryCode, DeliveryAssignment,
    Notification, Conversation, Message, Review, Favorite
)

User = get_user_model()

class ProductModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='seller'
        )
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.product = Product.objects.create(
            seller=self.user,
            category=self.category,
            name='Test Product',
            description='Test description',
            price=Decimal('100.00'),
            stock=10
        )

    def test_product_creation(self):
        """Test de création d'un produit"""
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.price, Decimal('100.00'))
        self.assertEqual(self.product.stock, 10)
        self.assertEqual(self.product.seller, self.user)
        self.assertFalse(self.product.is_sold_out)

    def test_product_discounted_price_no_discount(self):
        """Test prix sans réduction"""
        self.assertEqual(self.product.discounted_price, Decimal('100.00'))

    def test_product_discounted_price_with_discount(self):
        """Test prix avec réduction active"""
        Discount.objects.create(
            product=self.product,
            percentage=Decimal('20.00'),
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
            is_active=True
        )
        self.assertEqual(self.product.discounted_price, Decimal('80.00'))

    def test_product_is_sold_out(self):
        """Test statut rupture de stock"""
        self.product.stock = 0
        self.assertTrue(self.product.is_sold_out)

    def test_product_average_rating(self):
        """Test note moyenne"""
        buyer = User.objects.create_user(
            username='buyer',
            email='buyer@example.com',
            password='testpass123',
            user_type='buyer'
        )
        Review.objects.create(
            product=self.product,
            user=buyer,
            rating=4,
            comment='Good product'
        )
        Review.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            comment='Excellent'
        )
        self.assertEqual(self.product.average_rating, 4.5)

class CartModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='buyer'
        )
        self.seller = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            password='testpass123',
            user_type='seller'
        )
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Test Product',
            description='Test description',
            price=Decimal('50.00'),
            stock=10
        )
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_creation(self):
        """Test création panier"""
        self.assertEqual(self.cart.user, self.user)
        self.assertEqual(self.cart.total_items, 0)
        self.assertEqual(self.cart.subtotal, 0)

    def test_cart_item_creation(self):
        """Test ajout article au panier"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart_item.subtotal, Decimal('100.00'))
        self.assertEqual(self.cart.total_items, 2)
        self.assertEqual(self.cart.subtotal, Decimal('100.00'))

class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='buyer'
        )
        self.seller = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            password='testpass123',
            user_type='seller'
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
            estimated_days=3
        )

    def test_order_creation(self):
        """Test création commande"""
        order = Order.objects.create(
            user=self.user,
            seller=self.seller,
            total=Decimal('105.00'),
            shipping_address=self.address,
            shipping_option=self.shipping_option,
            delivery_mode='home',
            preferred_payment_method='cash',
            commission_payer='customer'
        )
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total, Decimal('105.00'))
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.delivery_mode, 'home')

    def test_qr_code_creation(self):
        """Test création QR Code"""
        order = Order.objects.create(
            user=self.user,
            seller=self.seller,
            total=Decimal('105.00'),
            shipping_address=self.address,
            delivery_mode='home',
            preferred_payment_method='cash'
        )
        
        qr_code = QRDeliveryCode.objects.create(
            order=order,
            delivery_address=f"{self.address.street_address}, {self.address.city}",
            delivery_mode=order.delivery_mode,
            preferred_payment_method=order.preferred_payment_method,
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        self.assertEqual(qr_code.order, order)
        self.assertFalse(qr_code.is_expired)
        self.assertFalse(qr_code.is_used)

class DiscountModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='seller'
        )
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.product = Product.objects.create(
            seller=self.user,
            category=self.category,
            name='Test Product',
            description='Test description',
            price=Decimal('100.00'),
            stock=10
        )

    def test_discount_validation(self):
        """Test validation des réductions"""
        # Test dates invalides
        with self.assertRaises(ValidationError):
            discount = Discount(
                product=self.product,
                percentage=Decimal('10.00'),
                start_date=timezone.now(),
                end_date=timezone.now() - timedelta(days=1)
            )
            discount.full_clean()

        # Test pourcentage invalide
        with self.assertRaises(ValidationError):
            discount = Discount(
                product=self.product,
                percentage=Decimal('150.00'),
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=1)
            )
            discount.full_clean()

    def test_active_discount(self):
        """Test réduction active"""
        discount = Discount.objects.create(
            product=self.product,
            percentage=Decimal('25.00'),
            start_date=timezone.now() - timedelta(hours=1),
            end_date=timezone.now() + timedelta(hours=1),
            is_active=True
        )
        self.assertEqual(self.product.discounted_price, Decimal('75.00'))
        self.assertEqual(self.product.active_discount_percentage, Decimal('25.00'))

class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_notification_creation(self):
        """Test création notification"""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='order_placed',
            message='Votre commande a été passée',
            related_object_id=1
        )
        self.assertEqual(notification.user, self.user)
        self.assertFalse(notification.is_read)
        self.assertEqual(notification.notification_type, 'order_placed')