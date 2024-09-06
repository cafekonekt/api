from django.urls import path
from shop.api.views import (
    MenuAPIView, 
    GetOutletAPIView, 
    ClientMenuAPIView, 
    CartView, 
    CheckoutAPIView, 
    GetTableAPIView,
    OrderAPIView
)

urlpatterns = [
    path('menu/', MenuAPIView.as_view(), name='menu'),
    path('client-menu/<slug:menu_slug>', ClientMenuAPIView.as_view(), name='category'),

    path('outlet/<slug:menu_slug>', GetOutletAPIView.as_view(), name='get-outlet'),
    path('tables/<slug:menu_slug>', GetTableAPIView.as_view(), name='get-tables'),
    
    path('cart/<slug:menu_slug>/', CartView.as_view(), name='cart'),
    path('cart/<slug:menu_slug>/<slug:item_id>/', CartView.as_view(), name='cart_item'),

    path('checkout/<slug:menu_slug>/', CheckoutAPIView.as_view(), name='checkout'),
    path('orders/<slug:menu_slug>/', OrderAPIView.as_view(), name='orders'),
]
