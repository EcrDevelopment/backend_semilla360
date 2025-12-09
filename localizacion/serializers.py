from rest_framework import serializers
from .models import Departamento, Provincia, Distrito


class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ['id', 'name']

class ProvinciaSerializer(serializers.ModelSerializer):
    department = DepartamentoSerializer(read_only=True)

    class Meta:
        model = Provincia
        fields = ['id', 'name', 'department']

class DistritoSerializer(serializers.ModelSerializer):
    province = ProvinciaSerializer(read_only=True)
    department = DepartamentoSerializer(read_only=True)

    class Meta:
        model = Distrito
        fields = ['id', 'name', 'province', 'department']