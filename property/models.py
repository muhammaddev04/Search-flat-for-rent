from django.db import models
from django.conf import settings

class Property(models.Model):
    PROPERTY_CHOICES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('room', 'Room'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    property_type = models.CharField(max_length=50, choices=PROPERTY_CHOICES)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rooms = models.PositiveIntegerField()
    area = models.DecimalField(max_digits=10, decimal_places=2)
    floor = models.PositiveIntegerField(null=True,blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100)
    address_details = models.TextField()
    amenities = models.TextField()
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.title} — {self.price} TJS'

class Property_Image(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/', null=True, blank=True)

    def __str__(self):
        return f"Image for {self.property.title}"

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} -> {self.property.title}'