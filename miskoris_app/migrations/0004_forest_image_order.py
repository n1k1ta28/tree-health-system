# Generated by Django 5.1.6 on 2025-03-23 16:46

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('miskoris_app', '0003_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='forest_image',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='images', to='miskoris_app.order'),
        ),
    ]
