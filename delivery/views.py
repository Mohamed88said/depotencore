from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse  # Correction de l'import
from .models import Location, Delivery
from .utils import get_exif_data, get_gps_info
from store.models import Order
from django.contrib.auth.models import User
import math

@login_required
def submit_location(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        if request.user != order.user:
            raise PermissionDenied("Vous n'êtes pas autorisé à soumettre une localisation pour cette commande.")
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Aucune commande trouvée avec cet ID.', 'latitude': None, 'longitude': None}, status=400)

    if request.method == 'POST':
        photo = request.FILES.get('photo')
        description = request.POST.get('description')
        latitude, longitude = None, None

        if photo:
            exif_data = get_exif_data(photo)
            latitude, longitude = get_gps_info(exif_data)

        location = Location.objects.create(
            user=request.user,
            photo=photo,
            latitude=latitude,
            longitude=longitude,
            description=description
        )
        Delivery.objects.create(order=order, location=location)
        return JsonResponse({'latitude': latitude, 'longitude': longitude})

    return render(request, 'delivery/submit_location.html', {'order': order})

@login_required
def suggest_location(request, order_id):
    order = Order.objects.get(id=order_id)
    if request.user != order.user:
        raise PermissionDenied("Vous n'êtes pas autorisé à voir les suggestions pour cette commande.")
    user_lat = request.GET.get('latitude')
    user_lon = request.GET.get('longitude')

    suggestions = []
    if user_lat and user_lon:
        user_lat, user_lon = float(user_lat), float(user_lon)
        locations = Location.objects.filter(latitude__isnull=False, longitude__isnull=False)
        for loc in locations:
            distance = haversine_distance(user_lat, user_lon, loc.latitude, loc.longitude)
            if distance < 5:  # Suggestions dans un rayon de 5 km
                suggestions.append({'location': loc, 'distance': distance})

    suggestions = sorted(suggestions, key=lambda x: x['distance'])
    return render(request, 'delivery/suggest_location.html', {
        'order': order,
        'suggestions': suggestions
    })
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points 
    on the Earth surface using the Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

@login_required
def assign_delivery(request, delivery_id):
    delivery = Delivery.objects.get(id=delivery_id)
    if request.user != delivery.order.seller and not request.user.is_staff:
        raise PermissionDenied("Vous n'êtes pas autorisé à assigner un livreur pour cette livraison.")
    if request.method == 'POST':
        delivery_person_id = request.POST.get('delivery_person')
        delivery_person = User.objects.get(id=delivery_person_id)
        delivery.delivery_person = delivery_person
        delivery.status = 'ASSIGNED'
        delivery.save()
        messages.success(request, "Livreur assigné avec succès.")
        return redirect('admin_panel:delivery_list')

    delivery_persons = User.objects.filter(groups__name='DeliveryPersons')
    return render(request, 'delivery/assign_delivery.html', {
        'delivery': delivery,
        'delivery_persons': delivery_persons
    })