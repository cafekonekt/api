# Generated by Django 4.2.4 on 2024-10-02 11:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0012_remove_addon_item_variant_addon_item_variant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cartitem',
            name='variant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='shop.itemvariant'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='variant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='shop.itemvariant'),
        ),
    ]