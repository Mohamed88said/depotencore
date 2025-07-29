import os
import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import importlib

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.core.asgi import get_asgi_application

admin_routing = importlib.import_module('admin_panel.routing')
chat_routing = importlib.import_module('chat.routing')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            admin_routing.websocket_urlpatterns +
            chat_routing.websocket_urlpatterns
        )
    ),
})