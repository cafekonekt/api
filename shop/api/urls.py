from django.urls import path
from shop.api.views import MenuAPIView, GetOutletAPIView

urlpatterns = [
    path('menu/<int:pk>/', MenuAPIView.as_view(), name='menu'),
    path('get-outlet/', GetOutletAPIView.as_view(), name='get-outlet'),
]
