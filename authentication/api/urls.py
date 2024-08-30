from django.urls import path
from authentication.api import views

urlpatterns = [
    path('', views.getRoutes, name='routes'),
    path('login/', views.CustomAuthToken.as_view(), name='custom_auth_token'),
    path('send-otp/', views.SendOTPView.as_view(), name='send_otp'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify_otp'),
]
