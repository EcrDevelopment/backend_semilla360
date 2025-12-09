from MySQLdb import IntegrityError
from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from rest_framework import serializers


from .models import Producto, Despacho, DetalleDespacho, ConfiguracionDespacho, GastosExtra, OrdenCompraDespacho, \
    Empresa, OrdenCompra, ProveedorTransporte, Transportista, Documento, Declaracion, ExpedienteDeclaracion, \
    TipoDocumento


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


#SERIALIZER PARA EDITAR UN FLETE:
class ProveedorTransporteEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProveedorTransporte
        fields = ['id', 'nombre_proveedor']

class TransportistaEditarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transportista
        fields = ['id', 'nombre_transportista']

class ProductoEditarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id', 'nombre_producto', 'codigo_producto', 'proveedor_marca']

class OrdenCompraEditarSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer()
    empresa = serializers.StringRelatedField()

    class Meta:
        model = OrdenCompra
        fields = ['id', 'numero_oc', 'producto', 'empresa', 'precio_producto', 'cantidad']

class OrdenCompraDespachoEditarSerializer(serializers.ModelSerializer):
    orden_compra = OrdenCompraSerializer()

    class Meta:
        model = OrdenCompraDespacho
        fields = ['id', 'orden_compra', 'cantidad_asignada', 'numero_recojo']

class ConfiguracionDespachoEditarSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionDespacho
        exclude = ['fecha_de_creacion', 'fecha_de_actualizacion']

class DetalleDespachoEditarSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleDespacho
        exclude = ['fecha_de_creacion', 'fecha_de_actualizacion', 'despacho']

class GastosExtraEditarSerializer(serializers.ModelSerializer):
    class Meta:
        model = GastosExtra
        exclude = ['fecha_de_creacion', 'fecha_de_actualizacion', 'despacho']

class DespachoEditarSerializer(serializers.ModelSerializer):
    proveedor = ProveedorTransporteSerializer()
    transportista = TransportistaSerializer()
    fecha_numeracion = serializers.DateTimeField(format="%d/%m/%Y")
    fecha_llegada = serializers.DateTimeField(format="%d/%m/%Y")

    class Meta:
        model = Despacho
        fields = [
            'id', 'dua', 'fecha_numeracion', 'fecha_llegada', 'carta_porte',
            'num_factura', 'transportista', 'proveedor', 'flete_pactado',
            'peso_neto_crt'
        ]

class EditarDespachoSerializer(serializers.ModelSerializer):
    proveedor = serializers.PrimaryKeyRelatedField(queryset=ProveedorTransporte.objects.all())
    transportista = serializers.PrimaryKeyRelatedField(queryset=Transportista.objects.all())
    nombre_proveedor = serializers.CharField(source='proveedor.nombre_proveedor', read_only=True)
    nombre_transportista = serializers.CharField(source='transportista.nombre_transportista', read_only=True)

    class Meta:
        model = Despacho
        fields = '__all__'
        extra_fields = ['nombre_proveedor', 'nombre_transportista']

class DespachoCompletoSerializer(serializers.Serializer):
    general = DespachoEditarSerializer()
    ordenes = serializers.SerializerMethodField()
    detalle_despacho = DetalleDespachoEditarSerializer(many=True)
    configuracion_despacho = ConfiguracionDespachoEditarSerializer(many=True)
    gastos_extra = GastosExtraEditarSerializer(many=True)

    def get_ordenes(self, obj):
        despacho = obj['general']
        ordenes_compra = despacho.ordenes_compra.all()
        ordenes_despacho = despacho.ordenes_despacho.all()
        return {
            "ordenes_compra": OrdenCompraEditarSerializer(ordenes_compra, many=True).data,
            "ordenes_despacho": OrdenCompraDespachoEditarSerializer(ordenes_despacho, many=True).data,
        }

class OrdenCompraDespachoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdenCompraDespacho
        fields = ['id', 'orden_compra', 'cantidad_asignada', 'numero_recojo']

class DetalleDespachoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleDespacho
        exclude = ['fecha_de_creacion', 'fecha_de_actualizacion', 'despacho']

class ConfiguracionDespachoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionDespacho
        exclude = ['fecha_de_creacion', 'fecha_de_actualizacion', 'despacho']

class GastosExtraWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GastosExtra
        exclude = ['fecha_de_creacion', 'fecha_de_actualizacion', 'despacho']

class DespachoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Despacho
        fields = [
            'dua', 'fecha_numeracion', 'fecha_llegada', 'carta_porte',
            'num_factura', 'transportista', 'proveedor',
            'flete_pactado', 'peso_neto_crt'
        ]

class DetalleDespachoEditarSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleDespacho
        fields = '__all__'

class GastosExtraEditarSerializer(serializers.ModelSerializer):
    class Meta:
        model = GastosExtra
        fields = '__all__'  # Incluye todos los campos

class EmpresaEditarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ['id', 'nombre_empresa']

class ProductoEditarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id', 'nombre_producto']

class OrdenCompraEditarSerializer(serializers.ModelSerializer):
    empresa = EmpresaEditarSerializer(read_only=True)
    producto = ProductoEditarSerializer(read_only=True)
    empresa_id = serializers.PrimaryKeyRelatedField(queryset=Empresa.objects.all(), write_only=True)
    producto_id = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all(), write_only=True)

    class Meta:
        model = OrdenCompra
        fields = [
            'id', 'numero_oc', 'precio_producto', 'cantidad',
             'empresa', 'producto', 'empresa_id', 'producto_id']

class OrdenCompraDespachoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdenCompraDespacho
        fields = '__all__'

    def validate(self, data):
        numero_oc = data.get('numero_oc')
        numero_recojo = data.get('numero_recojo')
        despacho = data.get('despacho')

        # Si es edición
        instance = self.instance

        # Verificar si ya existe una orden con el mismo número_oc y mismo despacho
        qs_oc = OrdenCompraDespacho.objects.filter(despacho=despacho, numero_oc=numero_oc)
        if instance:
            qs_oc = qs_oc.exclude(pk=instance.pk)
        if qs_oc.exists():
            raise serializers.ValidationError("Ya existe una orden con este N° OC en este despacho.")

        # Verificar si ya existe una orden con misma OC y mismo recojo
        if numero_recojo:
            qs_combo = OrdenCompraDespacho.objects.filter(
                despacho=despacho,
                numero_oc=numero_oc,
                numero_recojo=numero_recojo
            )
            if instance:
                qs_combo = qs_combo.exclude(pk=instance.pk)
            if qs_combo.exists():
                raise serializers.ValidationError("Ya existe una orden con este N° OC y N° Recojo en este despacho.")

        return data

class OrdenDespachoRowSerializer(serializers.ModelSerializer):
    numero_oc = serializers.SerializerMethodField()
    producto_nombre = serializers.SerializerMethodField()
    empresa_nombre = serializers.SerializerMethodField()
    precio_producto = serializers.SerializerMethodField()
    cantidad = serializers.SerializerMethodField()
    empresa_id = serializers.SerializerMethodField()

    class Meta:
        model = OrdenCompraDespacho
        fields = [
            'id',
            'numero_recojo',
            'cantidad_asignada',
            'numero_oc',
            'producto_nombre',
            'precio_producto',
            'cantidad',
            'empresa_id',
            'empresa_nombre',
        ]

    def get_numero_oc(self, obj):
        return obj.orden_compra.numero_oc if obj.orden_compra else None

    def get_producto_nombre(self, obj):
        return obj.orden_compra.producto.nombre_producto if obj.orden_compra and obj.orden_compra.producto else None

    def get_empresa_nombre(self, obj):
        return obj.orden_compra.empresa.nombre_empresa if obj.orden_compra and obj.orden_compra.empresa else None

    def get_precio_producto(self, obj):
        return obj.orden_compra.precio_producto if obj.orden_compra else None

    def get_cantidad(self, obj):
        return obj.orden_compra.cantidad if obj.orden_compra else None

    def get_empresa_id(self, obj):
        return obj.orden_compra.empresa_id if obj.orden_compra else None

    def validate(self, data):
        numero_oc = self.initial_data.get('numero_oc')
        numero_recojo = data.get('numero_recojo')
        empresa_id = self.initial_data.get('empresa_id')
        instance = self.instance

        if not Empresa.objects.filter(id=empresa_id).exists():
            raise serializers.ValidationError(f"La empresa con ID {empresa_id} no existe.")

        if numero_oc and numero_recojo:
            despacho_id = instance.despacho.id if instance else self.context['view'].kwargs.get('despacho_id')
            conflicto = OrdenCompraDespacho.objects.filter(
                orden_compra__numero_oc=numero_oc,
                numero_recojo=numero_recojo,
                despacho_id=despacho_id
            )
            if instance:
                conflicto = conflicto.exclude(id=instance.id)
            if conflicto.exists():
                raise serializers.ValidationError(
                    f"Ya existe un despacho con OC '{numero_oc}' y recojo '{numero_recojo}'."
                )
        return data

    def create(self, validated_data):
        numero_oc = self.initial_data.get('numero_oc')
        producto_nombre = self.initial_data.get('producto_nombre')
        empresa_id = self.initial_data.get('empresa_id')
        precio_producto = self.initial_data.get('precio_producto')
        cantidad = self.initial_data.get('cantidad')
        producto_id = self.initial_data.get('producto_id')

        try:
            if producto_id:
                producto = Producto.objects.get(id=producto_id)
            else:
                producto, _ = Producto.objects.get_or_create(nombre_producto=producto_nombre)
        except MultipleObjectsReturned:
            productos = Producto.objects.filter(nombre_producto=producto_nombre)
            raise serializers.ValidationError({
                "detalle": f"Se encontraron varios productos con el nombre '{producto_nombre}'.",
                "conflicto": True,
                "productos": [
                    {"id": p.id, "nombre_producto": p.nombre_producto, "proveedor": p.proveedor_marca}
                    for p in productos
                ]
            })

        orden_compra, _ = OrdenCompra.objects.get_or_create(
            numero_oc=numero_oc,
            defaults={
                'producto': producto,
                'empresa_id': empresa_id,
                'precio_producto': precio_producto,
                'cantidad': cantidad,
            }
        )

        despacho_id = self.context['view'].kwargs['despacho_id']

        try:
            return OrdenCompraDespacho.objects.create(
                despacho_id=despacho_id,
                orden_compra=orden_compra,
                numero_recojo=validated_data['numero_recojo'],
                cantidad_asignada=validated_data['cantidad_asignada'],
            )
        except IntegrityError:
            raise serializers.ValidationError({
                "detalle": (
                    f"Ya existe un despacho con con la misma combinación de OC y número de recojo "
                ),
                "conflicto": True,
                "tipo_error": "duplicado"
            })

    def update(self, instance, validated_data):
        orden_compra = instance.orden_compra
        producto_nombre = self.initial_data.get('producto_nombre')
        producto_id = self.initial_data.get('producto_id')

        try:
            if producto_id:
                # Si el frontend ya seleccionó un producto concreto
                producto = Producto.objects.get(id=producto_id)
            else:
                # Si viene solo el nombre, intentamos buscar/crear con control de duplicados
                producto, _ = Producto.objects.get_or_create(nombre_producto=producto_nombre)
        except MultipleObjectsReturned:
            productos = Producto.objects.filter(nombre_producto=producto_nombre)
            raise serializers.ValidationError({
                "detalle": f"Se encontraron varios productos con el nombre '{producto_nombre}'.",
                "conflicto": True,
                "productos": [
                    {"id": p.id, "nombre_producto": p.nombre_producto, "proveedor": p.proveedor_marca}
                    for p in productos
                ]
            })

        # Asignar el producto actualizado (solo si vino alguno)
        if producto_nombre or producto_id:
            orden_compra.producto = producto

        # Actualizar los demás campos de la orden de compra relacionada
        orden_compra.numero_oc = self.initial_data.get('numero_oc', orden_compra.numero_oc)
        orden_compra.precio_producto = self.initial_data.get('precio_producto', orden_compra.precio_producto)
        orden_compra.cantidad = self.initial_data.get('cantidad', orden_compra.cantidad)
        orden_compra.empresa_id = self.initial_data.get('empresa_id', orden_compra.empresa_id)
        orden_compra.save()

        # Actualizar los datos propios de la relación despacho-orden
        instance.numero_recojo = validated_data.get('numero_recojo', instance.numero_recojo)
        instance.cantidad_asignada = validated_data.get('cantidad_asignada', instance.cantidad_asignada)
        instance.save()

        return instance

class NewOrdenCompraDespachoSerializer(serializers.ModelSerializer):
    orden_compra = serializers.StringRelatedField(read_only=True)
    orden_compra_id = serializers.PrimaryKeyRelatedField(
        queryset=OrdenCompra.objects.all(),
        source="orden_compra",
        write_only=True
    )

    class Meta:
        model = OrdenCompraDespacho
        fields = [
            'id',
            'despacho',
            'orden_compra',
            'orden_compra_id',
            'cantidad_asignada',
            'numero_recojo',
            'fecha_de_creacion',
            'fecha_de_actualizacion',
        ]
        read_only_fields = ['fecha_de_creacion', 'fecha_de_actualizacion']

    def validate(self, attrs):
        despacho = attrs.get("despacho") or getattr(self.instance, "despacho", None)
        orden_compra = attrs.get("orden_compra") or getattr(self.instance, "orden_compra", None)
        numero_recojo = attrs.get("numero_recojo") or getattr(self.instance, "numero_recojo", None)

        if despacho and orden_compra and numero_recojo:
            existe = OrdenCompraDespacho.objects.filter(
                despacho=despacho,
                orden_compra=orden_compra,
                numero_recojo=numero_recojo,
            )
            if self.instance:  # si es update, excluir el mismo registro
                existe = existe.exclude(id=self.instance.id)
            if existe.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": "Ya existe esta Orden de Compra con el mismo número de recojo para este despacho."}
                )
        return attrs

class EmpresaEditarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ['id', 'nombre_empresa']

#AQUI ACABAN LOS SERIALIZER PARA EDITAR UN FLETE

class UsuarioMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name']

class DocumentoSerializer(serializers.ModelSerializer):
    usuario=UsuarioMiniSerializer(read_only=True)
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
    documentos_count = serializers.SerializerMethodField()

    def get_documentos_count(self, obj):
        return obj.documentos.count()

    class Meta:
        model = Declaracion
        fields = ['id', 'numero', 'anio', 'fecha_registro', 'documentos','documentos_count']

class PaginaAsignadaSerializer(serializers.Serializer):
    page = serializers.IntegerField(min_value=1)
    tipo = serializers.CharField()

class AsignarPaginasSerializer(serializers.Serializer):
    documento_id = serializers.IntegerField()
    asignaciones = PaginaAsignadaSerializer(many=True)

class ExpedienteDeclaracionListadoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='declaracion.id')
    numero_declaracion = serializers.CharField(source='declaracion.numero')
    anio_declaracion = serializers.IntegerField(source='declaracion.anio')
    cantidad_documentos = serializers.SerializerMethodField()

    class Meta:
        model = ExpedienteDeclaracion
        fields = [
            'id',  # ahora será el ID de la declaración
            'numero_declaracion',
            'anio_declaracion',
            'cantidad_documentos',
            'anio_fiscal',
            'mes_fiscal',
        ]

    def get_cantidad_documentos(self, obj):
        return ExpedienteDeclaracion.objects.filter(declaracion=obj.declaracion).count()

class DocumentoExpedienteSerializer(serializers.ModelSerializer):
    documento_id = serializers.IntegerField(source='documento.id')
    nombre_original = serializers.CharField(source='documento.nombre_original')
    fecha_subida = serializers.DateTimeField(source='documento.fecha_subida', format="%Y-%m-%d %H:%M")
    usuario = serializers.SerializerMethodField()
    archivo_url = serializers.SerializerMethodField()
    tipo = serializers.SerializerMethodField()  # ← Campo robusto

    class Meta:
        model = ExpedienteDeclaracion
        fields = [
            'id',
            'documento_id',
            'nombre_original',
            'fecha_subida',
            'usuario',
            'archivo_url',
            'tipo',
            'folio',
            'empresa',
            'anio_fiscal',
            'mes_fiscal',
            'orden_compra',
            'nota_ingreso',
        ]

    def get_usuario(self, obj):
        usuario = getattr(obj.documento, 'usuario', None)
        if usuario:
            return f"{usuario.first_name} {usuario.last_name}"
        return None

    def get_archivo_url(self, obj):
        if obj.documento and obj.documento.archivo:
            return obj.documento.archivo.url
        return None

    def get_tipo(self, obj):
        #print(f"DEBUG tipo: {repr(obj.tipo)} ({type(obj.tipo)}) (nombre:{obj.tipo.nombre})")
        return obj.tipo.nombre if obj.tipo else "Sin clasificar"

class ExpedienteDeclaracionFolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpedienteDeclaracion
        fields = ['id', 'folio']

class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoDocumento
        fields = '__all__'









