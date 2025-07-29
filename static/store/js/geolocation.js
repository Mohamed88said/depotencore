// Système de géolocalisation pour la Guinée
class GuineaGeolocation {
    constructor() {
        this.map = null;
        this.marker = null;
        this.userLocation = null;
        this.addresses = [];
        this.init();
    }

    init() {
        // Configuration des icônes Leaflet
        delete L.Icon.Default.prototype._getIconUrl;
        L.Icon.Default.mergeOptions({
            iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
            iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
            shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png'
        });
    }

    // Initialiser la carte
    initMap(containerId, options = {}) {
        const defaultOptions = {
            center: [9.5092, -13.7122], // Conakry
            zoom: 10,
            zoomControl: true,
            attributionControl: true
        };

        const mapOptions = { ...defaultOptions, ...options };
        
        this.map = L.map(containerId).setView(mapOptions.center, mapOptions.zoom);
        
        // Ajouter les tuiles OpenStreetMap
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(this.map);

        return this.map;
    }

    // Obtenir la position actuelle de l'utilisateur
    getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('La géolocalisation n\'est pas supportée'));
                return;
            }

            const options = {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000 // 5 minutes
            };

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const coords = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    };
                    this.userLocation = coords;
                    resolve(coords);
                },
                (error) => {
                    let message = 'Erreur de géolocalisation';
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            message = 'Permission de géolocalisation refusée';
                            break;
                        case error.POSITION_UNAVAILABLE:
                            message = 'Position non disponible';
                            break;
                        case error.TIMEOUT:
                            message = 'Délai de géolocalisation dépassé';
                            break;
                    }
                    reject(new Error(message));
                },
                options
            );
        });
    }

    // Ajouter un marqueur sur la carte
    addMarker(lat, lng, options = {}) {
        if (this.marker) {
            this.map.removeLayer(this.marker);
        }

        const markerOptions = {
            draggable: true,
            ...options
        };

        this.marker = L.marker([lat, lng], markerOptions).addTo(this.map);
        
        // Événement de déplacement du marqueur
        if (markerOptions.draggable) {
            this.marker.on('dragend', (e) => {
                const pos = e.target.getLatLng();
                this.onMarkerMove(pos.lat, pos.lng);
            });
        }

        return this.marker;
    }

    // Callback quand le marqueur est déplacé
    onMarkerMove(lat, lng) {
        // À surcharger dans les implémentations spécifiques
        console.log('Marqueur déplacé:', lat, lng);
    }

    // Rechercher des adresses
    async searchAddresses(query, region = null) {
        try {
            const url = new URL('/store/location/search/', window.location.origin);
            url.searchParams.append('q', query);
            if (region) {
                url.searchParams.append('region', region);
            }

            const response = await fetch(url);
            const data = await response.json();
            return data.results || [];
        } catch (error) {
            console.error('Erreur recherche adresses:', error);
            return [];
        }
    }

    // Géocodage inverse
    async reverseGeocode(lat, lng) {
        try {
            const response = await fetch('/store/location/api/reverse-geocode/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    latitude: lat,
                    longitude: lng
                })
            });

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Erreur géocodage inverse:', error);
            return null;
        }
    }

    // Obtenir le token CSRF
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    // Charger les préfectures d'une région
    async loadPrefectures(regionId) {
        try {
            const response = await fetch(`/store/location/api/prefectures/?region_id=${regionId}`);
            const data = await response.json();
            return data.prefectures || [];
        } catch (error) {
            console.error('Erreur chargement préfectures:', error);
            return [];
        }
    }

    // Charger les quartiers d'une préfecture
    async loadQuartiers(prefectureId) {
        try {
            const response = await fetch(`/store/location/api/quartiers/?prefecture_id=${prefectureId}`);
            const data = await response.json();
            return data.quartiers || [];
        } catch (error) {
            console.error('Erreur chargement quartiers:', error);
            return [];
        }
    }

    // Extraire les coordonnées GPS d'une photo (nécessite EXIF.js)
    extractGPSFromPhoto(file) {
        return new Promise((resolve, reject) => {
            if (!window.EXIF) {
                reject(new Error('Bibliothèque EXIF non disponible'));
                return;
            }

            EXIF.getData(file, function() {
                const lat = EXIF.getTag(this, "GPSLatitude");
                const lon = EXIF.getTag(this, "GPSLongitude");
                const latRef = EXIF.getTag(this, "GPSLatitudeRef");
                const lonRef = EXIF.getTag(this, "GPSLongitudeRef");

                if (lat && lon) {
                    const latitude = GuineaGeolocation.convertDMSToDD(lat, latRef);
                    const longitude = GuineaGeolocation.convertDMSToDD(lon, lonRef);
                    resolve({ latitude, longitude });
                } else {
                    reject(new Error('Pas de données GPS dans la photo'));
                }
            });
        });
    }

    // Convertir DMS en degrés décimaux
    static convertDMSToDD(dms, ref) {
        let dd = dms[0] + dms[1]/60 + dms[2]/3600;
        if (ref === "S" || ref === "W") {
            dd = dd * -1;
        }
        return dd;
    }

    // Calculer la distance entre deux points (formule de Haversine)
    static calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Rayon de la Terre en km
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    // Formater les coordonnées pour l'affichage
    static formatCoordinates(lat, lng, precision = 4) {
        return `${lat.toFixed(precision)}, ${lng.toFixed(precision)}`;
    }

    // Valider si les coordonnées sont en Guinée
    static isInGuinea(lat, lng) {
        return lat >= 7.0 && lat <= 13.0 && lng >= -15.0 && lng <= -7.0;
    }
}

// Initialisation automatique
document.addEventListener('DOMContentLoaded', function() {
    window.guineaGeo = new GuineaGeolocation();
});

// Fonctions utilitaires globales
window.GuineaGeoUtils = {
    // Autocomplétion d'adresses
    setupAddressAutocomplete: function(inputId, resultsId, onSelect) {
        const input = document.getElementById(inputId);
        const results = document.getElementById(resultsId);
        let timeout;

        input.addEventListener('input', function() {
            clearTimeout(timeout);
            const query = this.value.trim();
            
            if (query.length < 2) {
                results.innerHTML = '';
                results.style.display = 'none';
                return;
            }

            timeout = setTimeout(async () => {
                const addresses = await window.guineaGeo.searchAddresses(query);
                
                results.innerHTML = '';
                if (addresses.length > 0) {
                    addresses.forEach(addr => {
                        const div = document.createElement('div');
                        div.className = 'address-suggestion';
                        div.innerHTML = `
                            <strong>${addr.description}</strong><br>
                            <small class="text-muted">${addr.text}</small>
                            <span class="badge bg-secondary usage-badge ms-2">${addr.usage_count} utilisations</span>
                        `;
                        div.addEventListener('click', () => {
                            input.value = addr.description;
                            results.style.display = 'none';
                            if (onSelect) onSelect(addr);
                        });
                        results.appendChild(div);
                    });
                    results.style.display = 'block';
                } else {
                    results.style.display = 'none';
                }
            }, 300);
        });

        // Masquer les résultats quand on clique ailleurs
        document.addEventListener('click', function(e) {
            if (!input.contains(e.target) && !results.contains(e.target)) {
                results.style.display = 'none';
            }
        });
    },

    // Sélecteurs en cascade région > préfecture > quartier
    setupCascadingSelectors: function(regionId, prefectureId, quartierId) {
        const regionSelect = document.getElementById(regionId);
        const prefectureSelect = document.getElementById(prefectureId);
        const quartierSelect = document.getElementById(quartierId);

        regionSelect.addEventListener('change', async function() {
            const regionValue = this.value;
            prefectureSelect.innerHTML = '<option value="">Sélectionnez une préfecture</option>';
            quartierSelect.innerHTML = '<option value="">Sélectionnez un quartier</option>';

            if (regionValue) {
                const prefectures = await window.guineaGeo.loadPrefectures(regionValue);
                prefectures.forEach(pref => {
                    const option = document.createElement('option');
                    option.value = pref.id;
                    option.textContent = pref.name;
                    prefectureSelect.appendChild(option);
                });
            }
        });

        prefectureSelect.addEventListener('change', async function() {
            const prefectureValue = this.value;
            quartierSelect.innerHTML = '<option value="">Sélectionnez un quartier</option>';

            if (prefectureValue) {
                const quartiers = await window.guineaGeo.loadQuartiers(prefectureValue);
                quartiers.forEach(quart => {
                    const option = document.createElement('option');
                    option.value = quart.id;
                    option.textContent = quart.name;
                    quartierSelect.appendChild(option);
                });
            }
        });
    }
};