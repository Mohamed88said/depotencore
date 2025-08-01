from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from marketing.admin import admin_site
from channels.routing import ProtocolTypeRouter, URLRouter
from admin_panel import routing as admin_routing
from chat import routing as chat_routing

handler404 = 'store.views.custom_404'
handler500 = 'store.views.custom_500'

urlpatterns = [
    path('admin/', admin_site.urls),
    path('admin_panel/', include('admin_panel.urls', namespace='admin_panel')),
    path('accounts/', include('accounts.urls')),
    path('', include('store.urls', namespace='store')),
    path('blog/', include('blog.urls', namespace='blog')),
    path('dashboard/', include('dashboard.urls')),
    path('marketing/', include('marketing.urls', namespace='marketing')),
    path('returns/', include('returns.urls', namespace='returns')),
    path('chat/', include('chat.urls', namespace='chat')),
    path('delivery/', include('delivery.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

application = ProtocolTypeRouter({
    'websocket': URLRouter(
        admin_routing.websocket_urlpatterns +
        chat_routing.websocket_urlpatterns
    ),
})