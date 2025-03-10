from django.contrib.auth.models import User
from django.db import models

# Create your models here.

class Forest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100, unique=True)
    address = models.CharField(max_length=255)
    area = models.FloatField(help_text="Area in hectares")
    
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name

class Forest_image(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    forest = models.ForeignKey(Forest, on_delete=models.CASCADE, related_name='images')
    image = models.BinaryField()

    def __str__(self):
        return f"Image for {self.forest.name}"

# class TestClass(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     random_text = models.CharField(max_length=255)
#     random_float = models.FloatField()    