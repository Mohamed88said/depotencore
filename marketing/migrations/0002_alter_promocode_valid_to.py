# Generated by Django 4.2.16 on 2025-07-28 23:09

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='promocode',
            name='valid_to',
            field=models.DateTimeField(default=datetime.datetime(2025, 8, 27, 23, 9, 25, 881282, tzinfo=datetime.timezone.utc)),
        ),
    ]
