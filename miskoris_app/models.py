from django.contrib.postgres.fields import JSONField
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

    polygon_coords = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.name

class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    forest = models.ForeignKey(Forest, on_delete=models.CASCADE)
    start_date = models.DateField()
    paid_until = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Subscription for {self.forest.name} by {self.user.username}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    forest = models.ForeignKey(Forest, on_delete=models.CASCADE, related_name='orders')
    worker = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    bad_trees_found = models.BooleanField(default=False)
    is_subscription_order = models.BooleanField(default=False)

    def __str__(self):
        return f"Order for {self.forest.name} - {self.get_status_display()}"
    
class Forest_image(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    forest = models.ForeignKey(Forest, on_delete=models.CASCADE, related_name='images')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    image = models.BinaryField()
    latitude = models.FloatField(null=True, blank=True)  
    longitude = models.FloatField(null=True, blank=True)  

    def __str__(self):
        return f"Image for {self.forest.name} (Order ID: {self.order.id if self.order else 'None'})"

class Forest_document(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    forest = models.ForeignKey(Forest, on_delete=models.CASCADE, related_name='documents')
    document = models.BinaryField()
    filename = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.filename} for {self.forest.name}"

# class TestClass(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     random_text = models.CharField(max_length=255)
#     random_float = models.FloatField()    

class AnalyzedPhoto(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    forest = models.ForeignKey(Forest, on_delete=models.CASCADE, related_name='analyzed_images')
    image = models.BinaryField()
    analysis_result = models.TextField(blank=True, null=True)
    original_image = models.ForeignKey(Forest_image, on_delete=models.SET_NULL, null=True, blank=True, related_name='analyzed_versions')
    fixed = models.BooleanField(default=False)

    def __str__(self):
        return f"Analyzed Image for {self.forest.name}"
    
class Payment(models.Model):
    transaction_id = models.CharField(max_length=100, unique=True)
    payer_email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    forest = models.ForeignKey(Forest, on_delete=models.CASCADE, related_name='payments')
    order = models.OneToOneField(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment')
    subscription = models.OneToOneField(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.amount} {self.currency}"
    
class ForestNote(models.Model):
    forest = models.ForeignKey(Forest, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Note for {self.forest.name} - {self.created_at}"