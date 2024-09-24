from django.urls import path
from shortener.api.views import CreateShortURL, RedirectShortURL, AdGalleryList

urlpatterns = [
    path('shorten/', CreateShortURL.as_view(), name='create_short_url'),
    path('<str:short_code>/', RedirectShortURL.as_view(), name='redirect_short_url'),
    path('get-ads/', AdGalleryList.as_view(), name='get_large_ads'),
]
