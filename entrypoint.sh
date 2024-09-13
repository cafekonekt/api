#!/bin/sh

# Apply database migrations
python manage.py makemigrations --no-input
python manage.py migrate --no-input

# Create superuser
DJANGO_SUPERUSER_PASSWORD=cafekonekt@gmail.com python manage.py createsuperuser --name admin --email cafekonekt@gmail.com --no-input

# Collect static files
python manage.py collectstatic --no-input --clear
