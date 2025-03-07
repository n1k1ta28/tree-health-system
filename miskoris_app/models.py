from django.db import models

# Create your models here.

class Forest(models.Model):
    name = models.CharField(max_length=100, unique=True)
    address = models.CharField(max_length=255)
    area = models.FloatField(help_text="Area in hectares")
    
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name
    
# class TestClass(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     random_text = models.CharField(max_length=255)
#     random_float = models.FloatField()    