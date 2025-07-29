# Ecommerce Project

Plateforme de commerce électronique avec gestion des produits, retours, promotions, et communication en temps réel.

## Installation
1. Cloner le dépôt : `git clone <url>`
2. Créer un environnement virtuel : `python -m venv venv`
3. Activer l’environnement virtuel :
   - Windows : `venv\Scripts\activate`
   - Linux/Mac : `source venv/bin/activate`
4. Installer les dépendances : `pip install -r requirements.txt`
5. Configurer les variables d’environnement dans `.env` (voir `.env.example` pour les clés Stripe, PayPal, etc.).
6. Appliquer les migrations : `python manage.py migrate`
7. Lancer le serveur : `python manage.py runserver` (ou utiliser Daphne pour la production : `daphne -b 0.0.0.0 -p 8000 ecommerce_project.asgi:application`)

## Fonctionnalités
- **Gestion des produits** : Les vendeurs peuvent créer, modifier, et supprimer des produits (via `/store/`).
- **Gestion des retours** : Les acheteurs peuvent soumettre des demandes de retour, et les vendeurs peuvent les approuver/rejeter.
- **Paiements** : Intégration avec Stripe et PayPal pour les paiements et remboursements.
- **Notifications** : Système de notifications pour les avis, promotions, et demandes de retour.

## Gestion des retours
- **Pour les acheteurs** :
  - Accéder à l’historique des commandes via `/store/orders/`.
  - Soumettre une demande de retour depuis les détails d’une commande (`/store/order/<id>/`) pour les commandes livrées, dans les 30 jours.
  - Fournir une raison et une photo (facultative) via le formulaire.
- **Pour les vendeurs** :
  - Consulter les demandes de retour via `/returns/review/<id>/`.
  - Approuver ou rejeter les demandes, avec remboursement automatique via Stripe/PayPal si approuvé.
- **Administration** :
  - Les retours et remboursements sont consultables dans l’interface admin (`/admin/returns/returnrequest/` et `/admin/returns/refunded/`).

## Déploiement
- Utiliser Daphne pour gérer les connexions WebSocket (nécessaire pour l’application `chat` à venir).
- Configurer Redis pour `channels-redis` (voir `settings.py` pour `CHANNEL_LAYERS`).
- Passer les clés Stripe/PayPal en mode production (`PAYPAL_MODE='live'` dans `.env`).

## Prochaines étapes
- Implémenter l’application `chat` pour la communication en temps réel (voir Phase 2, étape 2.6).
- Ajouter des tests supplémentaires pour la validation des images dans les retours.
- Configurer les notifications push pour les messages et retours.

## Support
Pour toute question, contactez l’administrateur via l’interface admin ou à [votre-email@example.com].