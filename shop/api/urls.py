from django.urls import path
from shop.api.views import (
    FoodCategoryListCreateView,
    FoodItemListCreateView,
    FoodItemDetailView,
    AddonCategoryListCreateView,
    AddonCategoryDetailView,
    CartView,
    CheckoutAPIView,
    PaymentStatusAPIView,
    CashfreeWebhookView,
    OrderList,
    LiveOrders, 
    OrderDetailAPIView,
    OutletListView,
    OutletListCreateView,
    OutletDetailView,
    TableListView,
    TableListCreateView,
    TableDetailGetView,
    TableDetailView,
    AreaListCreateView,
    AreaDetailView,
    SocketSeller
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('menu/<slug:menu_slug>/', FoodCategoryListCreateView.as_view(), name='food-category'),

    path('food-items/', FoodItemListCreateView.as_view(), name='food-item'),
    path('food-items/<slug:slug>/', FoodItemDetailView.as_view(), name='food-item-detail'),

    path('addon-categories/', AddonCategoryListCreateView.as_view(), name='addon-category'),
    path('addon-categories/<int:pk>/', AddonCategoryDetailView.as_view(), name='addon-category-detail'),

    path('cart/<slug:menu_slug>/', CartView.as_view(), name='cart'),
    path('cart/<slug:menu_slug>/<slug:item_id>/', CartView.as_view(), name='cart_item'),

    path('checkout/<slug:menu_slug>/', CheckoutAPIView.as_view(), name='checkout'),
    path('payment/<slug:order_id>/', PaymentStatusAPIView.as_view(), name='payment-status'),
    path('cashfree/webhook/', CashfreeWebhookView.as_view(), name='cashfree-webhook'),

    path('orders/', OrderList.as_view(), name='orders'),
    path('live-orders/', LiveOrders.as_view(), name='live-orders'),
    path('live-orders/<slug:order_id>/', LiveOrders.as_view(), name='live-orders-detail'),
    path('order/<slug:order_id>/', OrderDetailAPIView.as_view(), name='orders'),

    path('outlet/<slug:menu_slug>', OutletListView.as_view(), name='outlet'),
    path('outlet/', OutletListCreateView.as_view(), name='outlet'),
    path('outlet/<int:pk>/', OutletDetailView.as_view(), name='outlet-detail'),

    path('tables/<slug:menu_slug>/', TableListView.as_view(), name='table'),
    path('table/<slug:table_id>/', TableDetailGetView.as_view(), name='table-detail'),
    path('tables/', TableListCreateView.as_view(), name='table'),

    path('area/', AreaListCreateView.as_view(), name='area'),
    path('area/<int:pk>/', AreaDetailView.as_view(), name='area-detail'),

    path('areas/<slug:area_slug>/', AreaDetailView.as_view(), name='area-detail'),
    path('subscription/', SocketSeller.as_view(), name='subscription'),
] 
if not settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)