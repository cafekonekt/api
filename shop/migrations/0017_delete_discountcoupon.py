# Generated by Django 4.2.4 on 2024-10-05 20:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0016_remove_order_transaction_status_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DiscountCoupon',
        ),
    ]
