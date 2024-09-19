from django.urls import path
from shortener.api.views import CreateShortURL, RedirectShortURL

urlpatterns = [
    path('shorten/', CreateShortURL.as_view(), name='create_short_url'),
    path('<str:short_code>/', RedirectShortURL.as_view(), name='redirect_short_url'),
]
