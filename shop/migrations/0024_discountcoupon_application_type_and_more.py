# Generated by Django 4.2.4 on 2024-10-20 16:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0023_itemrelation'),
    ]

    operations = [
        migrations.AddField(
            model_name='discountcoupon',
            name='application_type',
            field=models.CharField(choices=[('alluser', 'All User'), ('new', 'New User'), ('second', 'Second Order')], default='alluser', max_length=10),
        ),
        migrations.AlterField(
            model_name='fooditem',
            name='variant',
            field=models.ManyToManyField(blank=True, related_name='food_items', to='shop.variantcategory'),
        ),
    ]
