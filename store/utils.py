from django.db.models import Sum, Count, F
from .models import OrderItem, Product
import qrcode
from io import BytesIO
import base64

def get_sales_metrics(user):
    """
    Calcule les métriques de ventes pour un vendeur.
    """
    total_sales = OrderItem.objects.filter(
        product__seller=user,
        order__status='delivered'
    ).aggregate(total=Sum(F('quantity') * F('price')))['total'] or 0.00

    total_orders = OrderItem.objects.filter(
        product__seller=user
    ).values('order').distinct().count()

    products_in_stock = Product.objects.filter(
        seller=user, stock__gt=0, is_sold=False, sold_out=False
    ).count()

    return {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'products_in_stock': products_in_stock,
    }

def generate_qr_code_image(data, size=(300, 300)):
    """
    Génère une image QR Code à partir des données
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize(size)
    
    # Convertir en base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str

def calculate_delivery_distance(order):
    """
    Calcule la distance de livraison (simulation)
    En production, utiliser une API de géolocalisation
    """
    # Simulation basée sur la ville
    if order.shipping_address:
        city = order.shipping_address.city.lower()
        
        # Distances simulées pour différentes villes
        distances = {
            'conakry': 5.0,
            'kindia': 15.0,
            'boké': 25.0,
            'labé': 35.0,
            'mamou': 30.0,
            'faranah': 45.0,
            'kankan': 60.0,
            'nzérékoré': 55.0
        }
        
        for city_name, distance in distances.items():
            if city_name in city:
                return distance
    
    # Distance par défaut
    return 10.0

def calculate_commission(distance_km, base_rate=2.0):
    """
    Calcule la commission de livraison
    """
    return distance_km * base_rate