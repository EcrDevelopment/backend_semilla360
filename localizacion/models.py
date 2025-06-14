from django.db import models


class Departamento(models.Model):
    id = models.CharField(max_length=2, primary_key=True)  # Clave primaria con 2 caracteres
    name = models.CharField(max_length=45)

    class Meta:
        db_table = 'departamento'

    def __str__(self):
        return self.name

class Provincia(models.Model):
    id = models.CharField(max_length=4, primary_key=True)  # Clave primaria con 4 caracteres
    name = models.CharField(max_length=45)
    department = models.ForeignKey(Departamento, on_delete=models.CASCADE, related_name='provincias')

    class Meta:
        db_table = 'provincia'

    def __str__(self):
        return self.name

class Distrito(models.Model):
    id = models.CharField(max_length=6, primary_key=True)  # Clave primaria con 6 caracteres
    name = models.CharField(max_length=45, null=True, blank=True)
    province = models.ForeignKey(Provincia, on_delete=models.CASCADE, related_name='distritos')
    department = models.ForeignKey(Departamento, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'distrito'

    def __str__(self):
        return self.name

