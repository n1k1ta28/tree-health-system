# Generated by Django 5.0.6 on 2025-03-25 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('miskoris_app', '0007_remove_forest_document_order_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='forest_document',
            name='filename',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
