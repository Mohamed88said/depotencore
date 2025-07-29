from django.test import TestCase
from accounts.models import CustomUser
from store.models import Order
from .models import Location, Delivery
from .utils import haversine_distance

class DeliveryTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='12345',
            email='testuser@example.com',
            user_type='buyer'
        )
        self.order = Order.objects.create(
            user=self.user,
            total=100  # Utilisation de 'total'
        )
        self.location = Location.objects.create(
            user=self.user,
            description="En face de la mosquée Diaouné",
            latitude=9.6412,
            longitude=-13.5783
        )

    def test_submit_location(self):
        delivery = Delivery.objects.create(order=self.order, location=self.location)
        self.assertEqual(delivery.status, 'PENDING')
        self.assertEqual(delivery.location.description, "En face de la mosquée Diaouné")

    def test_submit_location_without_gps(self):
        location = Location.objects.create(
            user=self.user,
            description="Sans GPS",
            latitude=None,
            longitude=None
        )
        delivery = Delivery.objects.create(order=self.order, location=location)
        self.assertEqual(delivery.status, 'PENDING')
        self.assertEqual(delivery.location.description, "Sans GPS")

def test_haversine_distance(self):
    lat1, lon1 = 9.6412, -13.5783
    lat2, lon2 = 9.6500, -13.5700
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    expected_distance = 1.336  # Mise à jour de la valeur attendue
    self.assertAlmostEqual(distance, expected_distance, places=3)


def test_haversine_distance_same_point(self):
    lat, lon = 9.6412, -13.5783
    distance = haversine_distance(lat, lon, lat, lon)
    self.assertAlmostEqual(distance, 0.0, places=3)

def test_haversine_distance_known_cities(self):
    # Paris (48.8566, 2.3522) à Londres (51.5074, -0.1278)
    distance = haversine_distance(48.8566, 2.3522, 51.5074, -0.1278)
    expected_distance = 1,336  # Distance approximative en km
    self.assertAlmostEqual(distance, expected_distance, places=0)