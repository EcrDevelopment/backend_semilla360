from django.contrib.auth.models import User
from django.db import models
from datetime import timedelta
from django.utils import timezone
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    sede = models.CharField(max_length=100)  # Campo para almacenar la sede del usuario
    # Otros campos que desees agregar

    def __str__(self):
        return self.user.username

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.TextField( editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    active=models.BooleanField(default=True)

    def is_expired(self):
        #el token expira en 15 minutos
        return not self.active or timezone.now() > self.created_at + timedelta(minutes=15)

    def __str__(self):
        return str(self.token)