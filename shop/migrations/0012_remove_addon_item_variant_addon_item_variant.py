# Generated by Django 4.2.4 on 2024-09-29 14:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0011_remove_itemvariant_variant_itemvariant_variant'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='addon',
            name='item_variant',
        ),
        migrations.AddField(
            model_name='addon',
            name='item_variant',
            field=models.ManyToManyField(blank=True, null=True, related_name='addons', to='shop.itemvariant'),
        ),
    ]