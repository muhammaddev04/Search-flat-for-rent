from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('landlord', 'Landlord'),
        ('tenant', 'Tenant'),
    ]

    bio = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to='user_photos/', null=True, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tenant')
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.username


class EmailConfirm(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_confirm')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now=True)  # НАВ: то донем рамз кай сохта шуд (барои "аз нав фиристодан")

    def __str__(self):
        return self.user.username