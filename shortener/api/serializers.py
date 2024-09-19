from rest_framework import serializers
from shortener.models import ShortenedURL

class URLShortenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortenedURL
        fields = ['original_url', 'short_code', 'created_at']
        read_only_fields = ['short_code', 'created_at']
