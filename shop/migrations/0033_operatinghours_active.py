# Generated by Django 4.2.4 on 2024-12-08 20:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0032_alter_operatinghours_options_alter_payouts_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='operatinghours',
            name='active',
            field=models.BooleanField(default=True),
        ),
    ]
