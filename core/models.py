from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class User(AbstractUser):
    email = models.EmailField(unique=True)

    class Meta:
        permissions = [
            ('cancel_order','Can Cancel Order action')
        ]