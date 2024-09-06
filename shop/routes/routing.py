from django.urls import re_path
from shop.routes import consumers

websocket_urlpatterns = [
    re_path(r'ws/orders/(?P<order_id>\d+)/$', consumers.OrderConsumer.as_asgi()),
    re_path(r'ws/sellers/(?P<menu_slug>[\w-]+)/$', consumers.SellerConsumer.as_asgi()),
]