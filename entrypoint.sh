#!/bin/sh

# Apply database migrations
python manage.py makemigrations --no-input
python manage.py migrate --no-input

# Collect static files
python manage.py collectstatic --no-input --clear
