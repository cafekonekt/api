# Generated by Django 4.2.4 on 2024-12-15 15:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0035_remove_outlet_lite_outlet_outlet_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='foodcategory',
            name='category_image',
            field=models.ImageField(blank=True, null=True, upload_to='category_images/'),
        ),
        migrations.AddField(
            model_name='foodcategory',
            name='category_image_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='foodcategory',
            name='category_slug',
            field=models.SlugField(blank=True, max_length=100, null=True, unique=True),
        ),
    ]
