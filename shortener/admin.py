from django.contrib import admin
from shortener.models import ShortenedURL, AdGallery

admin.site.register(ShortenedURL)
admin.site.register(AdGallery)
