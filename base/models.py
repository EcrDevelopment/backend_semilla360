from django.utils import timezone

from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords


class BaseModelManager(models.Manager):
    def get_queryset(self):
        # Sobrescribe el queryset base para filtrar solo los activos
        return super().get_queryset().filter(state=True)

    def all_with_deleted(self):
        # Un método extra por si necesitas ver *todo*
        return super().get_queryset()


# --- 2. Tu Modelo Base Actualizado ---
class BaseCommonInfo(models.Model):
    """
    Modelo base abstracto con soft-delete y managers personalizados.
    """

    # --- Campos de Estado y Fechas ---
    state = models.BooleanField('Estado', default=True)
    created_date = models.DateTimeField('Fecha de Creación', auto_now_add=True)
    modified_date = models.DateTimeField('Fecha de Modificación', auto_now=True)
    deleted_date = models.DateTimeField('Fecha de Eliminación', null=True, blank=True)

    # --- Historial ---
    historical = HistoricalRecords(user_model=User, inherit=True)

    # --- ¡LOS MANAGERS! ---
    # El 'objects' por defecto ahora es nuestro manager filtrado
    objects = BaseModelManager()
    # 'all_objects' te permite acceder a todo, incluidos los borrados
    all_objects = models.Manager()

    # --- Propiedad para el Historial ---
    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    # --- ¡MÉTODO DELETE SOBRESCRITO! ---
    def delete(self, using=None, keep_parents=False):
        """
        Sobrescribe el delete() para implementar el borrado lógico (soft-delete).
        En lugar de borrar, marca el estado como Falso y guarda la fecha.
        """
        self.state = False
        self.deleted_date = timezone.now()
        self.save()  # Guarda los cambios en la BD

    def hard_delete(self):
        """
        Método extra por si *realmente* necesitas borrarlo de la BD.
        """
        super().delete()

    # --- Meta ---
    class Meta:
        abstract = True
        verbose_name = 'Modelo Base Común'
        verbose_name_plural = 'Modelos Base Comunes'


class BaseModel(BaseCommonInfo):
    """
    Hereda todos los campos comunes de BaseCommonInfo
    y añade la clave primaria 'id' estándar de Django (AutoField).

    Usar para la mayoría de modelos nuevos (ej. Empresa).
    """
    id = models.AutoField(primary_key=True)

    class Meta(BaseCommonInfo.Meta):  # Hereda la Meta del padre
        """Meta definition for BaseModel."""
        abstract = True  # ¡Esencial! Sigue siendo un molde.
        verbose_name = 'Modelo Base (con ID)'
        verbose_name_plural = 'Modelos Base (con ID)'
