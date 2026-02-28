from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('cajero', 'Cajero'),
        ('vendedor', 'Vendedor'),
        ('vigilante', 'Vigilante'),
        ('cliente', 'Cliente'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cliente')

    def __str__(self):
        return self.username