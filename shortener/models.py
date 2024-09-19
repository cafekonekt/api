import string
import random
from django.db import models
from django.utils.crypto import get_random_string

class ShortenedURL(models.Model):
    original_url = models.URLField(max_length=500)
    short_code = models.CharField(max_length=6, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.short_code:
            self.short_code = self.generate_short_code()
        super().save(*args, **kwargs)

    def generate_short_code(self):
        return get_random_string(6, allowed_chars=string.ascii_letters + string.digits)

    def __str__(self):
        return f"{self.original_url} -> {self.short_code}"
