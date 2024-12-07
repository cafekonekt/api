# Generated by Django 4.2.4 on 2024-12-07 08:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0005_customuser_dob'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(choices=[('admin', 'Admin'), ('owner', 'Owner'), ('chef', 'Chef'), ('outlet_manager', 'Outlet Manager'), ('staff', 'Staff'), ('customer', 'Customer')], max_length=20),
        ),
    ]
