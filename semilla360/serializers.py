from django.contrib.auth.models import User
from rest_framework import serializers

from semilla360.importaciones.models import Despacho


class DespachoSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source="proveedor.nombre_proveedor", read_only=True)
    transportista_nombre = serializers.CharField(source="transportista.nombre_transportista", read_only=True)
    ordenes_compra = serializers.SerializerMethodField()

    class Meta:
        model = Despacho
        fields = [
            'id', 'dua', 'fecha_numeracion', 'carta_porte', 'num_factura',
            'flete_pactado', 'peso_neto_crt', 'fecha_llegada', 'fecha_de_creacion',
            'proveedor_nombre', 'transportista_nombre', 'ordenes_compra'
        ]

    def get_ordenes_compra(self, obj):
        return [orden.id for orden in obj.ordenes_compra.all()]