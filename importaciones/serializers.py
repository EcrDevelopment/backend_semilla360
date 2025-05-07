from rest_framework import serializers
from .models import Producto, Despacho, DetalleDespacho, ConfiguracionDespacho, GastosExtra, OrdenCompraDespacho, \
    Empresa, OrdenCompra, ProveedorTransporte, Transportista,Documento,Declaracion


class FloatDecimalField(serializers.DecimalField):
    def to_representation(self, value):
        return float(value)

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'

class OrdenCompraSerializer(serializers.ModelSerializer):
    empresa = EmpresaSerializer(read_only=True)
    producto = ProductoSerializer(read_only=True)

    class Meta:
        model = OrdenCompra
        fields = '__all__'

class ProveedorTransporteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProveedorTransporte
        fields = '__all__'

class TransportistaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transportista
        fields = '__all__'

class OrdenCompraDespachoSerializer(serializers.ModelSerializer):
    orden_compra = OrdenCompraSerializer(read_only=True)

    class Meta:
        model = OrdenCompraDespacho
        fields = '__all__'


class ConfiguracionDespachoSerializer(serializers.ModelSerializer):
    gastos_nacionalizacion = FloatDecimalField(max_digits=10, decimal_places=2)
    margen_financiero = FloatDecimalField(max_digits=10, decimal_places=2)
    merma_permitida= FloatDecimalField(max_digits=10, decimal_places=2)
    precio_sacos_humedos = FloatDecimalField(max_digits=10, decimal_places=2)
    precio_sacos_mojados = FloatDecimalField(max_digits=10, decimal_places=2)
    precio_sacos_rotos = FloatDecimalField(max_digits=10, decimal_places=2)
    precio_prod = FloatDecimalField(max_digits=10, decimal_places=3)
    tipo_cambio_desc_ext = FloatDecimalField(max_digits=10, decimal_places=3)
    fecha_de_creacion = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")
    fecha_de_actualizacion = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")
    class Meta:
        model = ConfiguracionDespacho
        fields = '__all__'


class DetalleDespachoSerializer(serializers.ModelSerializer):
    merma = FloatDecimalField(max_digits=10, decimal_places=2)
    peso_llegada = FloatDecimalField(max_digits=10, decimal_places=2)
    peso_salida = FloatDecimalField(max_digits=10, decimal_places=2)
    fecha_de_creacion = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")
    fecha_de_actualizacion = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")
    class Meta:
        model = DetalleDespacho
        fields = '__all__'


class GastosExtraSerializer(serializers.ModelSerializer):
    class Meta:
        model = GastosExtra
        fields = '__all__'



class DespachoSerializer(serializers.ModelSerializer):
    proveedor = ProveedorTransporteSerializer(read_only=True)
    transportista = TransportistaSerializer(read_only=True)
    ordenes_compra = OrdenCompraSerializer(many=True, read_only=True)
    ordenes_despacho = OrdenCompraDespachoSerializer(many=True, read_only=True)
    flete_pactado = FloatDecimalField(max_digits=10, decimal_places=2)
    peso_neto_crt = FloatDecimalField(max_digits=10, decimal_places=2)
    fecha_llegada = serializers.DateTimeField(format="%d/%m/%Y")
    fecha_numeracion = serializers.DateTimeField(format="%d/%m/%Y")
    fecha_de_creacion = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")
    fecha_de_actualizacion = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")
    configuracion_despacho = ConfiguracionDespachoSerializer(source='configuraciondespacho_set', many=True,read_only=True)
    detalle_despacho = DetalleDespachoSerializer(source='detalledespacho_set', many=True, read_only=True)
    gastos_extra = GastosExtraSerializer(source='gastosextra_set', many=True, read_only=True)

    class Meta:
        model = Despacho
        fields = '__all__'


class DocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documento
        fields = '__all__'



class DeclaracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Declaracion
        fields = ['id', 'numero', 'anio']


class DocumentoListadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documento
        fields = ['id', 'nombre_original', 'archivo', 'fecha_subida']


class DeclaracionConDocumentosSerializer(serializers.ModelSerializer):
    documentos = DocumentoListadoSerializer(many=True, read_only=True)

    class Meta:
        model = Declaracion
        fields = ['id', 'numero', 'anio', 'fecha_registro', 'documentos']
