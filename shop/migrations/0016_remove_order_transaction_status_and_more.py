# Generated by Django 4.2.4 on 2024-10-04 21:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0015_alter_order_payment_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='transaction_status',
        ),
        migrations.AlterField(
            model_name='order',
            name='payment_method',
            field=models.CharField(choices=[('online', 'Online'), ('credit_card', 'Credit Card'), ('net_banking', 'Net Banking'), ('upi', 'UPI'), ('wallet', 'Wallet'), ('credit_card_emi', 'Credit Card EMI'), ('debit_card_emi', 'Debit Card EMI'), ('cardless_emis', 'Cardless EMIs'), ('pay_later', 'Pay Later'), ('cash', 'Cash')], default='online', max_length=100),
        ),
    ]
