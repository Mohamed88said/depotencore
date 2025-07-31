from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from unittest.mock import patch
import json
from .models import (
    Product, Category, Cart, CartItem, Order, OrderItem, Address, 
    ShippingOption, QRDeliveryCode, Favorite, Review
)

User = get_user_model()

class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_page_loads(self):
        """Test que la page d'accueil se charge"""
        response = self.client.get(reverse('store:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bienvenue')

class ProductViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
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
            price=Decimal('100.00'),
            stock=10
        )

    def test_product_list_view(self):
        """Test liste des produits"""
        response = self.client.get(reverse('store:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

    def test_product_detail_view(self):
        """Test détail produit"""
        response = self.client.get(reverse('store:product_detail', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
        self.assertContains(response, '100.00')

    def test_product_search(self):
        """Test recherche produits"""
        response = self.client.get(reverse('store:product_list') + '?q=Test')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

    def test_product_filter_by_category(self):
        """Test filtre par catégorie"""
        response = self.client.get(reverse('store:product_list') + '?category=Test Category')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

class CartViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
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
            price=Decimal('100.00'),
            stock=10
        )

    def test_cart_view_anonymous(self):
        """Test panier utilisateur anonyme"""
        response = self.client.get(reverse('store:cart'))
        self.assertEqual(response.status_code, 302)  # Redirection vers login

    def test_cart_view_authenticated(self):
        """Test panier utilisateur connecté"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('store:cart'))
        self.assertEqual(response.status_code, 200)

    def test_add_to_cart(self):
        """Test ajout au panier"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('store:add_to_cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que l'article est dans le panier
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().product, self.product)

    def test_update_cart_quantity(self):
        """Test mise à jour quantité panier"""
        self.client.login(username='testuser', password='testpass123')
        
        # Ajouter au panier d'abord
        self.client.post(reverse('store:add_to_cart', args=[self.product.id]))
        cart = Cart.objects.get(user=self.user)
        cart_item = cart.items.first()
        
        # Mettre à jour la quantité
        response = self.client.post(
            reverse('store:update_cart', args=[cart_item.id]),
            {'quantity': 3}
        )
        self.assertEqual(response.status_code, 302)
        
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)

    def test_remove_from_cart(self):
        """Test suppression du panier"""
        self.client.login(username='testuser', password='testpass123')
        
        # Ajouter au panier d'abord
        self.client.post(reverse('store:add_to_cart', args=[self.product.id]))
        cart = Cart.objects.get(user=self.user)
        cart_item = cart.items.first()
        
        # Supprimer du panier
        response = self.client.get(reverse('store:remove_from_cart', args=[cart_item.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(cart.items.count(), 0)

class CheckoutViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
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
            price=Decimal('100.00'),
            stock=10
        )
        self.address = Address.objects.create(
            user=self.user,
            full_name='Test User',
            street_address='123 Test St',
            city='Test City',
            postal_code='12345',
            country='Test Country',
            is_default=True
        )
        self.shipping_option = ShippingOption.objects.create(
            name='Standard',
            cost=Decimal('5.00'),
            estimated_days=3,
            is_active=True
        )

    def test_checkout_view_empty_cart(self):
        """Test checkout avec panier vide"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('store:checkout'))
        self.assertEqual(response.status_code, 302)  # Redirection car panier vide

    def test_checkout_view_with_items(self):
        """Test checkout avec articles"""
        self.client.login(username='testuser', password='testpass123')
        
        # Ajouter au panier
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        
        response = self.client.get(reverse('store:checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

    def test_process_payment_cod(self):
        """Test traitement paiement à la livraison"""
        self.client.login(username='testuser', password='testpass123')
        
        # Ajouter au panier
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        
        # Données de commande
        data = {
            'delivery_mode': 'home',
            'preferred_payment_method': 'cash',
            'commission_payer': 'customer',
            'address_mode': 'existing',
            'address': self.address.id,
            'shipping_option': self.shipping_option.id,
            'payment_method': 'cod'
        }
        
        response = self.client.post(reverse('store:process_payment'), data)
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que la commande a été créée
        self.assertTrue(Order.objects.filter(user=self.user).exists())
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.delivery_mode, 'home')
        self.assertEqual(order.preferred_payment_method, 'cash')
        
        # Vérifier que le QR Code a été créé
        self.assertTrue(QRDeliveryCode.objects.filter(order=order).exists())

class FavoriteViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
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
            price=Decimal('100.00'),
            stock=10
        )

    def test_toggle_favorite_add(self):
        """Test ajout aux favoris"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('store:toggle_favorite', args=[self.product.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'added')
        
        # Vérifier que le favori a été créé
        self.assertTrue(Favorite.objects.filter(user=self.user, product=self.product).exists())

    def test_toggle_favorite_remove(self):
        """Test suppression des favoris"""
        self.client.login(username='testuser', password='testpass123')
        
        # Créer un favori d'abord
        Favorite.objects.create(user=self.user, product=self.product)
        
        response = self.client.post(
            reverse('store:toggle_favorite', args=[self.product.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'removed')
        
        # Vérifier que le favori a été supprimé
        self.assertFalse(Favorite.objects.filter(user=self.user, product=self.product).exists())

    def test_favorites_list_view(self):
        """Test liste des favoris"""
        self.client.login(username='testuser', password='testpass123')
        
        # Créer un favori
        Favorite.objects.create(user=self.user, product=self.product)
        
        response = self.client.get(reverse('store:favorites'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

class QRPaymentViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
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
        self.order = Order.objects.create(
            user=self.user,
            seller=self.seller,
            total=Decimal('105.00'),
            shipping_address=self.address,
            delivery_mode='home',
            preferred_payment_method='cash',
            status='shipped'
        )
        self.qr_code = QRDeliveryCode.objects.create(
            order=self.order,
            delivery_address=f"{self.address.street_address}, {self.address.city}",
            delivery_mode=self.order.delivery_mode,
            preferred_payment_method=self.order.preferred_payment_method,
            expires_at=timezone.now() + timedelta(days=7)
        )

    def test_view_qr_code(self):
        """Test affichage QR Code"""
        self.client.login(username='seller', password='testpass123')
        response = self.client.get(reverse('store:view_qr_code', args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'QR Code de livraison')

    def test_scan_qr_payment_valid(self):
        """Test scan QR Code valide"""
        response = self.client.get(reverse('store:scan_qr_payment', args=[self.qr_code.code]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paiement de la commande')

    def test_scan_qr_payment_expired(self):
        """Test scan QR Code expiré"""
        # Expirer le QR Code
        self.qr_code.expires_at = timezone.now() - timedelta(hours=1)
        self.qr_code.save()
        
        response = self.client.get(reverse('store:scan_qr_payment', args=[self.qr_code.code]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'QR Code expiré')

    def test_scan_qr_payment_not_found(self):
        """Test scan QR Code inexistant"""
        response = self.client.get(reverse('store:scan_qr_payment', args=['invalid-code']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'QR Code non trouvé')

    def test_process_qr_payment_cash(self):
        """Test paiement espèces via QR"""
        data = {
            'payment_method': 'cash',
            'customer_confirms': 'true',
            'delivery_confirms': 'true'
        }
        
        response = self.client.post(
            reverse('store:process_qr_payment', args=[self.qr_code.code]),
            data
        )
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que la commande est marquée comme livrée
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'delivered')
        
        # Vérifier que le QR Code est marqué comme utilisé
        self.qr_code.refresh_from_db()
        self.assertTrue(self.qr_code.is_used)

class AuthenticationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='buyer'
        )

    def test_login_required_views(self):
        """Test vues nécessitant une connexion"""
        protected_urls = [
            reverse('store:cart'),
            reverse('store:checkout'),
            reverse('store:favorites'),
            reverse('store:notifications'),
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/accounts/login/', response.url)

    def test_seller_only_views(self):
        """Test vues réservées aux vendeurs"""
        self.client.login(username='testuser', password='testpass123')
        
        # L'utilisateur est un buyer, pas un seller
        response = self.client.get(reverse('store:product_create'))
        self.assertEqual(response.status_code, 403)

class OrderHistoryTest(TestCase):
    def setUp(self):
        self.client = Client()
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
        self.order = Order.objects.create(
            user=self.user,
            seller=self.seller,
            total=Decimal('105.00'),
            status='delivered'
        )

    def test_order_history_view(self):
        """Test historique des commandes"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('store:order_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Commande #{self.order.id}')

    def test_order_detail_view(self):
        """Test détail commande"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('store:order_detail', args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Commande #{self.order.id}')

class NotificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='buyer'
        )

    def test_notifications_view(self):
        """Test page notifications"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('store:notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'notifications')