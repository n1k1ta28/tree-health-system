# Generated by Django 5.1.6 on 2025-04-19 13:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('miskoris_app', '0012_forest_image_latitude_forest_image_longitude'),
    ]

    operations = [
        migrations.AddField(
            model_name='analyzedphoto',
            name='fixed',
            field=models.BooleanField(default=False),
        ),
    ]
