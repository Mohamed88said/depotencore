from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import math
import logging

logger = logging.getLogger(__name__)

def get_exif_data(image_path):
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if not exif_data:
            logger.warning(f"No EXIF data found in image: {image_path}")
            return None
        exif = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            exif[tag] = value
        logger.info(f"EXIF data extracted successfully for image: {image_path}")
        return exif
    except Exception as e:
        logger.error(f"Error extracting EXIF from {image_path}: {e}")
        return None

def get_gps_info(exif_data):
    if not exif_data or 'GPSInfo' not in exif_data:
        logger.warning("No GPSInfo found in EXIF data")
        return None, None
    gps_info = {}
    for key, value in exif_data['GPSInfo'].items():
        gps_tag = GPSTAGS.get(key, key)
        gps_info[gps_tag] = value

    def convert_to_degrees(value):
        d, m, s = value
        return d + (m / 60.0) + (s / 3600.0)

    latitude = gps_info.get('GPSLatitude')
    latitude_ref = gps_info.get('GPSLatitudeRef')
    longitude = gps_info.get('GPSLongitude')
    longitude_ref = gps_info.get('GPSLongitudeRef')

    if latitude and longitude and latitude_ref and longitude_ref:
        lat = convert_to_degrees(latitude)
        if latitude_ref != 'N':
            lat = -lat
        lon = convert_to_degrees(longitude)
        if longitude_ref != 'E':
            lon = -lon
        logger.info(f"GPS coordinates extracted: lat={lat}, lon={lon}")
        return lat, lon
    logger.warning("Incomplete GPS data in EXIF")
    return None, None

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcule la distance en kilomètres entre deux points GPS."""
    R = 6371  # Rayon de la Terre en km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c