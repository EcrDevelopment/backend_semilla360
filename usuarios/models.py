from django.contrib.auth.models import User, Group, Permission
from django.db import models
from datetime import timedelta
from django.utils import timezone
from base.models import BaseModel
from localizacion.models import Departamento, Distrito, Provincia


class Empresa(BaseModel):
    nombre = models.CharField(max_length=255)
    direccion = models.TextField(blank=True, null=True)
    ruc = models.CharField(max_length=11, unique=True)  # RUC u otro identificador único de la empresa

    class Meta:
        db_table = 'empresa_perfil'

    def __str__(self):
        return self.nombre

    def tiene_direcciones(self):
        return self.direcciones.exists()

class Direccion(BaseModel):
    empresa = models.ForeignKey(Empresa, related_name='direcciones', on_delete=models.CASCADE)
    direccion = models.TextField(max_length=2500)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE)
    distrito = models.ForeignKey(Distrito, on_delete=models.CASCADE)

    class Meta:
        db_table = 'direccion'

    def __str__(self):
        return f"{self.direccion} - {self.distrito.name}, {self.provincia.name}, {self.departamento.name}"



class UserProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
    telefono = models.CharField(max_length=20, null=True, blank=True)
    empresa = models.ForeignKey(Empresa, related_name='empresa', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'perfil'

    def __str__(self):
        return f"Perfil de {self.user.username}"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.TextField( editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    active=models.BooleanField(default=True)

    def is_expired(self):
        #el token expira en 15 minutos
        return not self.active or timezone.now() > self.created_at + timedelta(minutes=15)

    class Meta:
        db_table = 'password_reset_token'

    def __str__(self):
        return str(self.token)