# Generated by Django 4.2.4 on 2024-09-13 12:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0012_alter_addoncategory_menu'),
    ]

    operations = [
        migrations.AddField(
            model_name='addon',
            name='addon_type',
            field=models.CharField(choices=[('veg', 'Veg'), ('egg', 'Egg'), ('nonveg', 'Non-Veg')], default='veg', max_length=10),
        ),
    ]