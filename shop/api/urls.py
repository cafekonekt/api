from django.urls import path
from shop.api.views import MenuAPIView, GetOutletAPIView, ClientMenuAPIView, CartView

urlpatterns = [
    path('menu/', MenuAPIView.as_view(), name='menu'),
    path('client-menu/<slug:menu_slug>', ClientMenuAPIView.as_view(), name='category'),
    path('outlet/<slug:slug>', GetOutletAPIView.as_view(), name='get-outlet'),
    path('cart/<slug:menu_slug>/', CartView.as_view(), name='cart'),
    path('cart/<slug:menu_slug>/<int:item_id>/', CartView.as_view(), name='cart_item'),
]
