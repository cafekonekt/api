# Generated by Django 4.2.4 on 2024-10-27 04:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0028_order_offer'),
    ]

    operations = [
        migrations.AddField(
            model_name='foodcategory',
            name='order',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='fooditem',
            name='order',
            field=models.PositiveIntegerField(default=0),
        ),
    ]