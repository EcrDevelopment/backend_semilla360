from rest_framework import serializers
from .models import Departamento, Provincia, Distrito

class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = '__all__'

class ProvinciaSerializer(serializers.ModelSerializer):
    department = DepartamentoSerializer()

    class Meta:
        model = Provincia
        fields = '__all__'

class DistritoSerializer(serializers.ModelSerializer):
    province = ProvinciaSerializer()
    department = DepartamentoSerializer()

    class Meta:
        model = Distrito
        fields = '__all__'