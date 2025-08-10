# LuxeShop - Premium E-commerce Platform for Guinea

## 📋 Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Technical Architecture](#technical-architecture)
4. [User Types](#user-types)
5. [Order Process](#order-process)
6. [Delivery System](#delivery-system)
7. [Payment System](#payment-system)
8. [Returns Management](#returns-management)
9. [Moderation System](#moderation-system)
10. [Real-time Notifications](#real-time-notifications)
11. [Installation and Setup](#installation-and-setup)
12. [Project Structure](#project-structure)
13. [APIs and Integrations](#apis-and-integrations)
14. [Security](#security)
15. [Testing](#testing)
16. [Deployment](#deployment)
17. [Roadmap and Future Developments](#roadmap-and-future-developments)

---

## 🎯 Overview

**LuxeShop** is a comprehensive e-commerce platform specifically designed for the Guinean market. It enables local sellers to create their online stores and buyers to order products with a **cash-on-delivery only** payment system via secure QR Code.

### 🌟 Project Highlights

- **Cash-on-delivery only** - Adapted to the local Guinean context
- **Secure QR Code system** - For delivery transactions
- **Advanced geolocation** - Guinea-specific address system
- **Courier marketplace** - Network of independent delivery personnel
- **Automatic moderation** - Quality control for products and users
- **Real-time notifications** - WebSocket for smooth experience
- **Advanced seller dashboard** - Statistics and forecasts with Prophet
- **Complete returns system** - Automated refund management

---

## 🚀 Key Features

### For Buyers
- **Navigation and search**: Catalog with advanced filters (price, category, brand, color, etc.)
- **Smart cart**: Quantity management, automatic total calculation
- **Favorites**: Save preferred products
- **Review system**: Product ratings and comments
- **Order history**: Complete purchase tracking
- **Multiple addresses**: Delivery address management
- **Geolocation**: Precise location for delivery
- **Return requests**: Simplified refund process
- **Notifications**: Real-time order alerts

### For Sellers
- **Custom store**: Seller profile with business information
- **Product management**: Complete CRUD with multiple images
- **Advanced dashboard**: Detailed statistics and forecasts
- **Order management**: Status tracking and updates
- **Delivery system**: Choice between personal delivery or marketplace
- **Review responses**: Customer interaction
- **Returns management**: Approve/reject requests
- **Moderation**: Product submission for validation
- **Promotions**: Temporary discount system

### For Couriers
- **Delivery marketplace**: Real-time available deliveries
- **Courier profile**: Status and vehicle management
- **Commission system**: Distance-based compensation
- **Ratings**: Customer rating system
- **Geolocation**: Real-time delivery tracking

### For Administrators
- **Admin panel**: Complete management interface
- **Product moderation**: Approval/rejection with notifications
- **Report management**: User report processing
- **Global statistics**: Platform performance metrics
- **User management**: Account activation/deactivation
- **Data exports**: CSV for external analysis

---

## 🏗️ Technical Architecture

### Technology Stack
- **Backend**: Django 4.2.16 (Python)
- **Frontend**: Bootstrap 5.3 + Vanilla JavaScript
- **Database**: SQLite (development) / PostgreSQL (production)
- **WebSocket**: Django Channels + Redis
- **Payments**: Stripe + PayPal (ready integration)
- **Geolocation**: Leaflet.js + OpenStreetMap
- **Forecasting**: Prophet (Facebook) for statistics
- **Images**: Pillow for processing
- **Emails**: Gmail SMTP configured

### Django Applications

1. **accounts** - User and profile management
2. **store** - E-commerce core (products, orders, cart)
3. **admin_panel** - Custom administration interface
4. **marketing** - Loyalty program and promo codes
5. **returns** - Returns and refunds system
6. **delivery** - Delivery management and geolocation
7. **chat** - Real-time messaging (WebSocket)
8. **blog** - Blog system for sellers
9. **dashboard** - Seller dashboards with statistics

---

## 👥 User Types

### 1. Buyers
```python
user_type = 'buyer'
```
**Capabilities:**
- Browse and purchase products
- Manage cart and favorites
- Place orders with cash-on-delivery payment
- Leave reviews and ratings
- Request returns
- Communicate with sellers

**Restrictions:**
- Cannot sell products
- Limited access to statistics

### 2. Sellers
```python
user_type = 'seller'
```
**Capabilities:**
- Create and manage a store
- Add/modify/delete products
- Manage orders and deliveries
- Access advanced statistics
- Respond to customer reviews
- Manage returns
- Choose delivery mode (personal or marketplace)

**Verification Process:**
- Registration with business information
- Product moderation by admins
- Seller profile with ratings

### 3. Couriers
```python
user_type = 'delivery'
```
**Capabilities:**
- Access delivery marketplace
- Accept/decline deliveries
- Manage availability status
- Receive ratings
- Track earnings and statistics

**Compensation System:**
- Distance-based commission (€2/km by default)
- Possible bonuses defined by sellers
- Payment according to who covers costs (seller or customer)

### 4. Administrators
```python
is_staff = True
```
**Full Capabilities:**
- Moderation of all content
- User management
- Access to global statistics
- Report processing
- Platform configuration

---

## 🛒 Order Process

### 1. Selection and Cart Addition
```python
# Adding a product to cart
cart, created = Cart.objects.get_or_create(user=request.user)
cart_item, created = CartItem.objects.get_or_create(
    cart=cart, 
    product=product,
    defaults={'quantity': 1}
)
```

### 2. Delivery Configuration
The buyer chooses:
- **Delivery mode**: Home delivery or store pickup
- **Preferred payment method**: Cash, card, or PayPal
- **Commission payer**: Customer or seller
- **Delivery address**: Existing or new
- **GPS location**: Precise position (optional)

### 3. QR Code Generation
```python
# Automatic QR Code creation
qr_code = QRDeliveryCode.objects.create(
    order=order,
    delivery_address=f"{address.street_address}, {address.city}",
    delivery_mode=order.delivery_mode,
    preferred_payment_method=order.preferred_payment_method,
    expires_at=timezone.now() + timedelta(days=7)
)
```

### 4. Delivery Mode Choice (Seller)
The seller can:
- **Deliver personally**: No commission
- **Assign specific courier**: Direct choice
- **Publish on marketplace**: Let couriers apply

### 5. Cash-on-Delivery Payment
- Courier has customer scan QR Code
- Final payment method choice
- Double confirmation (customer + courier) for cash
- Automatic processing for card/PayPal

---

## 🚚 Delivery System

### Guinea Geolocation
The system integrates Guinea's administrative structure:

```python
# Hierarchical structure
GuineaRegion (8 regions)
├── GuineaPrefecture (33 prefectures)
    └── GuineaQuartier (neighborhoods by prefecture)
        └── GuineaAddress (precise addresses)
```

**Supported Regions:**
- Conakry (capital)
- Kindia, Boké, Labé, Mamou, Faranah, Kankan, Nzérékoré

### Courier Marketplace
```python
class DeliveryAssignment(models.Model):
    order = models.OneToOneField(Order)
    vendor = models.ForeignKey(User, related_name='delivery_assignments')
    delivery_person = models.ForeignKey(User, null=True, blank=True)
    distance_km = models.FloatField()
    commission_amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(choices=STATUS_CHOICES)
```

**Process:**
1. Seller publishes delivery with commission
2. Available couriers see the offer
3. First to accept gets the delivery
4. Real-time tracking until delivery

### Commission Calculation
```python
def calculate_commission(distance_km, base_rate=2.0, bonus=0.0):
    return (distance_km * base_rate) + bonus
```

---

## 💳 Payment System

### Principle: Cash-on-delivery only
Unlike traditional e-commerce, **all payments are made on delivery** via QR Code.

### Secure QR Code
```python
class QRDeliveryCode(models.Model):
    order = models.OneToOneField(Order)
    code = models.CharField(max_length=50, unique=True)  # Generated UUID
    delivery_address = models.TextField()
    delivery_mode = models.CharField(choices=DELIVERY_MODES)
    preferred_payment_method = models.CharField(choices=PAYMENT_METHODS)
    special_instructions = models.TextField(blank=True)
    expires_at = models.DateTimeField()  # 7 days by default
    is_used = models.BooleanField(default=False)
    scanned_at = models.DateTimeField(null=True)
```

### Supported Payment Methods
1. **Cash**: Double confirmation (customer + courier)
2. **Bank card**: Ready Stripe integration
3. **PayPal**: Ready PayPal integration

### Security
- QR Code expires after 7 days
- Unique non-guessable code (UUID)
- Order and status verification
- No amount visible in QR Code
- All transaction logs

---

## 🔄 Returns Management

### Process for Buyer
1. **Conditions**: Delivered order + within 30 days
2. **Form**: Reason + optional photo
3. **Validation**: Automatic condition verification
4. **Notification**: Seller automatically alerted

### Process for Seller
```python
class ReturnRequest(models.Model):
    order = models.ForeignKey(Order)
    user = models.ForeignKey(User)
    reason = models.TextField(max_length=500)
    image = models.ImageField(upload_to='returns/images/', blank=True)
    status = models.CharField(choices=STATUS_CHOICES, default='PENDING')
    rejection_reason = models.TextField(blank=True)
```

**Possible Actions:**
- **Approve**: Automatic refund according to payment method
- **Reject**: With mandatory reason

### Automatic Refunds
```python
# For cash-on-delivery
if return_request.order.payment_method == 'cod':
    Refund.objects.create(
        return_request=return_request,
        amount=order.total,
        method='manual',  # Manual refund by seller
        status='PENDING'
    )

# For Stripe (ready)
stripe.Refund.create(
    charge=order.charge_id,
    amount=int(order.total * 100)  # Cents
)
```

---

## 🛡️ Moderation System

### Product Moderation
All new products go through moderation:

```python
class ProductModeration(models.Model):
    product = models.OneToOneField(Product)
    status = models.CharField(choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'), 
        ('rejected', 'Rejected')
    ])
    moderator = models.ForeignKey(User, null=True)
    reason = models.TextField(blank=True)
```

### User Reports
```python
class Report(models.Model):
    reporter = models.ForeignKey(User, related_name='reports_made')
    user = models.ForeignKey(User, related_name='reports_received', null=True)
    product = models.ForeignKey(Product, null=True)
    reason = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(choices=STATUS_CHOICES)
```

### Automatic Moderation
- **10 open reports** = Automatic account deactivation
- **Automatic notifications** to admins and concerned users
- **Complete history** of all moderation actions

---

## 🔔 Real-time Notifications

### WebSocket with Django Channels
```python
# ASGI Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}
```

### Notification Types
- **New orders** for sellers
- **Status changes** for buyers
- **Return requests** for sellers
- **Product moderation** for sellers
- **Chat messages** between users
- **Reports** for admins

### WebSocket Consumer
```python
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
```

---

## 📊 Seller Dashboard and Statistics

### Available Metrics
- **Monthly sales**: Revenue with trends
- **Daily orders**: Activity volume
- **Stock per product**: Inventory management
- **Popular products**: Top 5 best sellers
- **Customer reviews**: Average ratings per product
- **Product requests**: Customer interest
- **Conversion rate**: Views → Sales

### Forecasting with Prophet
```python
from prophet import Prophet

# Sales forecast generation
df = pd.DataFrame({
    'ds': [pd.to_datetime(label) for label in sales_labels],
    'y': sales_data
})
model = Prophet()
model.fit(df)
future = model.make_future_dataframe(periods=horizon, freq='M')
forecast = model.predict(future)
```

### Automatic Alerts
- **Low stock**: Notification when stock < defined threshold
- **New orders**: Real-time alert
- **Negative reviews**: Notification for quick response

---

## 🌍 Geolocation System

### Guinea Administrative Structure
```python
# Pre-loaded data via management command
python manage.py populate_guinea_data
```

### Geo Features
- **Address autocompletion**: Smart search
- **Cascading selectors**: Region → Prefecture → Neighborhood
- **GPS extraction from photos**: Automatic coordinates from EXIF
- **Distance calculation**: Haversine formula
- **Location suggestions**: Based on proximity

### Geolocation API
```javascript
// JavaScript class for geolocation
class GuineaGeolocation {
    async getCurrentPosition() { /* ... */ }
    async searchAddresses(query, region) { /* ... */ }
    async reverseGeocode(lat, lng) { /* ... */ }
    static calculateDistance(lat1, lon1, lat2, lon2) { /* ... */ }
}
```

---

## 💬 Chat and Messaging System

### Real-time Chat
```python
class Conversation(models.Model):
    initiator = models.ForeignKey(User, related_name='conversations_initiated')
    recipient = models.ForeignKey(User, related_name='conversations_received')
    product = models.ForeignKey(Product)
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    conversation = models.ForeignKey(Conversation)
    sender = models.ForeignKey(User)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
```

### WebSocket Consumer
```python
class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data):
        message_content = json.loads(text_data)['message']
        # Save and broadcast message
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_content,
                'sender': self.scope['user'].username,
            }
        )
```

---

## 🎯 Marketing and Loyalty

### Loyalty Program
```python
class LoyaltyPoint(models.Model):
    user = models.ForeignKey(User)
    points = models.PositiveIntegerField()
    earned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True)
    description = models.CharField(max_length=255)

# Automatic attribution: 1 point per €10 purchase
points = int(order.total // 10)
LoyaltyPoint.objects.create(
    user=order.user,
    points=points,
    description=f"Purchase order #{order.id}"
)
```

### Promo Codes
```python
class PromoCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    max_uses = models.PositiveIntegerField()
    uses = models.PositiveIntegerField(default=0)
```

### Integrated Blog
Sellers can create blog posts to promote their products:
```python
class Post(models.Model):
    author = models.ForeignKey(User)  # Seller
    title = models.CharField(max_length=200)
    content = models.TextField()
    products = models.ManyToManyField(Product, blank=True)  # Associated products
```

---

## 🔧 Installation and Setup

### Prerequisites
- Python 3.8+
- Redis (for WebSocket)
- Node.js (for Tailwind CSS)

### Installation
```bash
# 1. Clone the project
git clone <repository-url>
cd ecommerce_project

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt
npm install

# 4. Database configuration
python manage.py migrate

# 5. Load Guinea data
python manage.py populate_guinea_data

# 6. Create superuser
python manage.py createsuperuser

# 7. Collect static files
python manage.py collectstatic

# 8. Start Redis (in another terminal)
redis-server

# 9. Start development server
python manage.py runserver
# or for production with WebSocket:
daphne -b 0.0.0.0 -p 8000 ecommerce_project.asgi:application
```

### Environment Variables (.env)
```env
# Base
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Stripe (optional)
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# PayPal (optional)
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_CLIENT_SECRET=your-paypal-secret
PAYPAL_MODE=sandbox

# reCAPTCHA
RECAPTCHA_PUBLIC_KEY=your-recaptcha-public-key
RECAPTCHA_PRIVATE_KEY=your-recaptcha-private-key
```

---

## 📁 Project Structure

```
ecommerce_project/
├── accounts/                 # User management
│   ├── models.py            # CustomUser, Profile, SellerProfile
│   ├── forms.py             # Registration forms
│   ├── views.py             # Authentication views
│   └── signals.py           # Automatic profile creation
├── store/                   # E-commerce core
│   ├── models.py            # Product, Order, Cart, etc.
│   ├── views.py             # Main views
│   ├── forms.py             # Product forms
│   ├── utils.py             # Utility functions
│   └── management/commands/ # Django commands
├── admin_panel/             # Administration
│   ├── models.py            # Moderation, Reports
│   ├── views.py             # Admin views
│   └── consumers.py         # WebSocket admin
├── delivery/                # Deliveries
│   ├── models.py            # Location, Delivery
│   ├── utils.py             # Geolocation
│   └── views.py             # Delivery management
├── returns/                 # Returns
│   ├── models.py            # ReturnRequest, Refund
│   ├── views.py             # Return process
│   └── signals.py           # Automatic notifications
├── marketing/               # Marketing
│   ├── models.py            # LoyaltyPoint, PromoCode
│   └── admin.py             # Custom admin interface
├── chat/                    # Messaging
│   ├── consumers.py         # WebSocket chat
│   └── routing.py           # WebSocket routes
├── blog/                    # Seller blog
│   ├── models.py            # Post, Comment
│   └── views.py             # Article management
├── dashboard/               # Dashboards
│   └── views.py             # Advanced statistics
├── templates/               # HTML templates
│   ├── base.html            # Base template
│   ├── store/               # Store templates
│   ├── accounts/            # User templates
│   ├── admin_panel/         # Admin templates
│   └── dashboard/           # Dashboard templates
├── static/                  # Static files
│   ├── css/                 # CSS styles
│   ├── js/                  # JavaScript
│   └── img/                 # Images
└── media/                   # Uploaded files
    ├── products/            # Product images
    ├── profile_pics/        # Profile photos
    └── returns/             # Return images
```

---

## 🔌 APIs and Integrations

### Internal APIs
- `/store/api/categories/autocomplete/` - Category autocompletion
- `/store/location/search/` - Address search
- `/store/location/api/reverse-geocode/` - Reverse geocoding
- `/store/apply-promo-code/` - Promo code application
- `/vendor/products/bulk-action/` - Bulk actions

### Ready External Integrations
- **Stripe**: Card payments
- **PayPal**: PayPal payments
- **OpenStreetMap**: Maps and geolocation
- **Gmail SMTP**: Email sending
- **reCAPTCHA**: Anti-spam protection

### WebSocket Endpoints
- `ws://domain/ws/notifications/` - User notifications
- `ws://domain/ws/chat/<conversation_id>/` - Real-time chat

---

## 🔒 Security

### Authentication
- **Django Allauth**: Complete authentication management
- **User types**: Role separation
- **Email verification**: Disabled by default (adapted to local context)

### Data Protection
- **CSRF Protection**: Tokens on all forms
- **XSS Protection**: Automatic template escaping
- **SQL Injection**: Django ORM
- **File Upload Security**: Type and size validation

### Permissions
```python
# Security decorators
@login_required
def vendor_only_view(request):
    if request.user.user_type != 'seller':
        raise PermissionDenied("Access reserved for sellers")
```

### Secure Configuration
```python
# settings.py - Security configuration
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# CSP Headers
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://js.stripe.com")
```

---

## 🧪 Testing

### Test Coverage
The project includes comprehensive tests for:

```python
# Model tests
class StoreModelTests(TestCase):
    def test_product_discounted_price(self):
        # Test discounted price calculation
    
    def test_order_total_calculation(self):
        # Test order total calculation

# View tests
class StoreViewTests(TestCase):
    def test_add_to_cart(self):
        # Test cart addition
    
    def test_checkout_process(self):
        # Test checkout process

# Integration tests
class FullWorkflowIntegrationTest(TestCase):
    def test_complete_purchase_workflow(self):
        # Test complete purchase → delivery → payment workflow
```

### Running Tests
```bash
# All tests
python manage.py test

# Specific tests
python manage.py test store.tests
python manage.py test returns.tests
python manage.py test admin_panel.tests

# With coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

---

## 🚀 Deployment

### Development
```bash
# Simple development server
python manage.py runserver

# With WebSocket (recommended)
daphne -b 0.0.0.0 -p 8000 ecommerce_project.asgi:application
```

### Production
```bash
# 1. Production configuration
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com']

# 2. PostgreSQL database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'luxeshop_db',
        'USER': 'luxeshop_user',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# 3. Redis for WebSocket
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('redis-server', 6379)],
        },
    },
}

# 4. ASGI server with Daphne
daphne -b 0.0.0.0 -p 8000 ecommerce_project.asgi:application

# 5. Nginx as reverse proxy
# Nginx configuration to serve static files
```

### Docker (suggested configuration)
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "ecommerce_project.asgi:application"]
```

---

## 🎯 Roadmap and Future Developments

### Phase 1: Core Features ✅
- [x] Multi-role authentication system
- [x] Product and catalog management
- [x] Cart and order process
- [x] QR Code for cash-on-delivery payment
- [x] Delivery system with marketplace
- [x] Automated returns management
- [x] Content moderation
- [x] Real-time notifications

### Phase 2: Advanced Improvements 🚧
- [ ] **Mobile app**: React Native or Flutter
- [ ] **Mobile payments**: Orange Money, MTN Mobile Money
- [ ] **AI for recommendations**: Product recommendation system
- [ ] **Chatbot**: Automated customer support
- [ ] **Advanced analytics**: Google Analytics, Facebook Pixel
- [ ] **Multi-language**: French/English/local languages support

### Phase 3: Expansion 📈
- [ ] **Advanced multi-vendor**: Dynamic commissions
- [ ] **B2B marketplace**: Wholesale sales
- [ ] **Banking integration**: Partnerships with local banks
- [ ] **Advanced logistics**: Warehouses and distribution centers
- [ ] **Public API**: For third-party integrations
- [ ] **Affiliate program**: Referral system

### Phase 4: Innovation 🔮
- [ ] **Augmented reality**: Virtual try-on
- [ ] **Blockchain**: Product traceability
- [ ] **IoT**: Real-time delivery tracking
- [ ] **Machine Learning**: Fraud detection
- [ ] **Voice Commerce**: Voice orders

---

## 📈 Metrics and KPIs

### Business Metrics
- **GMV** (Gross Merchandise Value): Total sales volume
- **Conversion rate**: Visitors → Buyers
- **Average cart**: Average order value
- **Return rate**: Percentage of returns
- **NPS** (Net Promoter Score): Customer satisfaction

### Technical Metrics
- **Response time**: Page performance
- **Uptime**: Platform availability
- **Error rate**: 4xx/5xx errors
- **WebSocket usage**: Active connections

### Seller Metrics
- **Processing time**: Order preparation delay
- **Approval rate**: Approved vs submitted products
- **Average rating**: Customer satisfaction
- **Response rate**: Message responsiveness

---

## 🛠️ Maintenance and Monitoring

### Logs and Debugging
```python
# Logging configuration
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'django.log',
        },
    },
    'loggers': {
        'store': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

### Maintenance Commands
```bash
# Clean expired sessions
python manage.py clearsessions

# Clean old notifications
python manage.py cleanup_notifications

# Update seller statistics
python manage.py update_seller_stats

# Check data integrity
python manage.py check_data_integrity
```

### Recommended Monitoring
- **Sentry**: Error monitoring
- **New Relic**: Performance monitoring
- **Uptime Robot**: Availability monitoring
- **Google Analytics**: Traffic analysis

---

## 🤝 Contribution and Development

### Code Standards
- **PEP 8**: Python style
- **Black**: Automatic formatting
- **Flake8**: Linting
- **Type hints**: Type annotations

### Git Workflow
```bash
# Main branches
main          # Production
develop       # Development
feature/*     # New features
hotfix/*      # Urgent fixes
```

### Pre-commit Tests
```bash
# Run all tests
python manage.py test

# Check style
flake8 .
black --check .

# Check migrations
python manage.py makemigrations --check
```

---

## 📞 Support and Contact

### Technical Documentation
- **Django**: https://docs.djangoproject.com/
- **Channels**: https://channels.readthedocs.io/
- **Bootstrap**: https://getbootstrap.com/docs/
- **Leaflet**: https://leafletjs.com/reference.html

### Developer Contact
- **Email**: mohamedsaiddiallo88@gmail.com
- **GitHub**: [Link to repository]

### User Support
- **FAQ**: `/help/faq/`
- **Contact**: Integrated contact form
- **Support chat**: Via admin interface

---

## 📄 License

This project is under MIT license. See the `LICENSE` file for more details.

---

## 🙏 Acknowledgments

- **Django Community**: Exceptional framework
- **Bootstrap Team**: Modern user interface
- **OpenStreetMap**: Free cartographic data
- **Guinean Community**: Feedback and suggestions

---

*Last updated: January 2025*
*Version: 1.0.0*

---

## 🔍 Technical FAQ

### Q: Why cash-on-delivery only?
**A:** Adapted to the Guinean context where trust in online payments is limited. QR Code secures the process while keeping physical payment.

### Q: How does the geolocation system work?
**A:** Uses Guinea's administrative structure (Region > Prefecture > Neighborhood) with GPS coordinates for precise location.

### Q: Can other payment methods be added?
**A:** Yes, the architecture is ready for Orange Money, MTN Mobile Money, etc. Just need to add API integrations.

### Q: How to handle scaling?
**A:** 
- PostgreSQL database with replication
- Redis Cluster for WebSocket
- CDN for static files
- Load balancer for Django servers

### Q: Is the system multilingual?
**A:** Currently in French, but Django i18n is configured to easily add other languages.

---

*This README is a living document that evolves with the project. Feel free to contribute to improve it!*