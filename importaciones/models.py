import hashlib
import os

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from django.contrib.auth.models import User
from django.db import models

from base.models import BaseModel


#TABLAS DEL SERVIDOR STARSOFT

class OrdenCompraStarsoft(models.Model):
    CNUMERO = models.CharField(max_length=13, primary_key=True)
    CNUMIMP = models.CharField(max_length=13, null=True, blank=True)
    CITEM = models.CharField(max_length=3)
    CCODPROVE = models.CharField(max_length=11, null=True, blank=True)
    FEMISION = models.DateTimeField(null=True, blank=True)
    CCODARTIC = models.CharField(max_length=20, null=True, blank=True)
    CCODREFER = models.CharField(max_length=40, null=True, blank=True)
    CDESARTIC = models.CharField(max_length=200, null=True, blank=True)
    CUNIDAD = models.CharField(max_length=6, null=True, blank=True)
    CUNIREFER = models.CharField(max_length=6, null=True, blank=True)
    NFACTOR = models.FloatField(default=0)
    NCANTIDAD = models.FloatField(default=0)
    NPREUNITA = models.FloatField(default=0)
    NDSCPORCE = models.FloatField(default=0)
    NDESCUENT = models.FloatField(default=0)
    NPRENETO = models.FloatField(default=0)
    NPREREF = models.FloatField(default=0)
    NCANTUNID = models.FloatField(default=0)
    NTOTVENT = models.FloatField(default=0)
    NCANTENTR = models.FloatField(default=0)
    NCANSALDO = models.FloatField(default=0)
    CESTADO = models.CharField(max_length=2, null=True, blank=True)
    NRECIBIDO = models.FloatField(default=0)
    NVALORCIF = models.FloatField(default=0)
    NPORCIF = models.FloatField(default=0)
    NADVALOR = models.FloatField(default=0)
    CLLAVE = models.CharField(max_length=13, null=True, blank=True)
    CMARCA = models.CharField(max_length=1, null=True, blank=True)
    TIPORDEN = models.CharField(max_length=2, null=True, blank=True)
    CCOMENT1 = models.TextField(null=True, blank=True)
    NFACTOR1 = models.FloatField(default=0)
    NCANNAC = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    NFACTORPRV = models.DecimalField(max_digits=15, decimal_places=6, default=0)
    NPRECIODES = models.DecimalField(max_digits=15, decimal_places=6, default=0)
    NTPRECIODES = models.DecimalField(max_digits=15, decimal_places=6, default=0)
    #SALDO_REGDOC = models.DecimalField(max_digits=18, decimal_places=6, default=0)

    class Meta:
        db_table = 'IMPORD'
        managed = False  # Indicamos que Django no debería crear esta tabla

class OrdenCompraDetStarsoft(models.Model):
    CNUMERO= models.OneToOneField(
        OrdenCompraStarsoft,  # Relación con el modelo principal
        on_delete=models.CASCADE,
        db_column='CNUMERO',  # Coincide con el campo de la tabla
        primary_key=True,
        related_name = 'detalles'
    )
    #cnumero = models.CharField(max_length=13, primary_key=True)
    CNUMIMP = models.CharField(max_length=13, null=True, blank=True)
    CCODPROVE = models.CharField(max_length=11, null=True, blank=True)
    CDESPROVE = models.CharField(max_length=100, null=True, blank=True)
    FEMISION = models.DateTimeField(null=True, blank=True)
    # FENTREGA = models.DateTimeField(null=True, blank=True)
    NIMPORTE = models.FloatField(default=0)
    CCODMONIM = models.CharField(max_length=4, null=True, blank=True)
    NEQUIV_US = models.FloatField(default=0)
    NTIPCAMBI = models.FloatField(default=0)
    CESTADO = models.CharField(max_length=4, null=True, blank=True)
    CLIQADUAN = models.CharField(max_length=20, null=True, blank=True)
    CSOLIINSP = models.CharField(max_length=16, null=True, blank=True)
    CGUIATRAN = models.CharField(max_length=16, null=True, blank=True)
    NLIQVALOR = models.FloatField(default=0)
    LLIQREAL = models.BooleanField(default=False)
    NSALDOTOT = models.FloatField(default=0)
    NSALLIQUI = models.FloatField(default=0)
    COBSERVAC = models.CharField(max_length=100, null=True, blank=True)
    LREAL = models.BooleanField(default=False)
    TIPORDEN = models.CharField(max_length=2, null=True, blank=True)
    CNUMLIQUI = models.CharField(max_length=20, null=True, blank=True)
    NADVALOR = models.FloatField(default=0)
    CVOLANTE = models.CharField(max_length=13, null=True, blank=True)
    CLLAVE = models.CharField(max_length=13, null=True, blank=True)
    CCONVER = models.CharField(max_length=3, null=True, blank=True)
    CPACKING = models.CharField(max_length=13, null=True, blank=True)
    TIPCONVER = models.CharField(max_length=3, null=True, blank=True)
    TIPPREIMP = models.CharField(max_length=3, null=True, blank=True)
    CSITUACION = models.CharField(max_length=2, null=True, blank=True)
    CTERM = models.TextField(null=True, blank=True)
    CFLETE = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    CSEGURO = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    CETAPA = models.CharField(max_length=8, null=True, blank=True)
    CCODCLI = models.CharField(max_length=11, null=True, blank=True)
    CDESCLI = models.CharField(max_length=100, null=True, blank=True)
    CCODMARCA = models.CharField(max_length=20, null=True, blank=True)
    CDESMARCA = models.CharField(max_length=30, null=True, blank=True)
    COD_AUDITORIA = models.CharField(max_length=12, null=True, blank=True)
    CFLETE_MN = models.DecimalField(max_digits=15, decimal_places=6, default=0)
    CSEGURO_MN = models.DecimalField(max_digits=15, decimal_places=6, default=0)
    TIPODOCUMENTO = models.CharField(max_length=2, default='OI')

    class Meta:
        db_table = 'IMPORC'
        managed = False


    def __str__(self):
        return f"{self.cnumero}"

class Proveedor(models.Model):
    PRVCCODIGO = models.CharField(max_length=11, primary_key=True, db_column='PRVCCODIGO')
    PRVCNOMBRE = models.CharField(max_length=100, blank=True, null=True, db_column='PRVCNOMBRE')
    PRVCDIRECC = models.CharField(max_length=100, blank=True, null=True, db_column='PRVCDIRECC')
    PRVCLOCALI = models.CharField(max_length=25, blank=True, null=True, db_column='PRVCLOCALI')
    PRVCPAISAC = models.CharField(max_length=15, blank=True, null=True, db_column='PRVCPAISAC')
    PRVCTELEF1 = models.CharField(max_length=30, blank=True, null=True, db_column='PRVCTELEF1')
    PRVCFAXACR = models.CharField(max_length=15, blank=True, null=True, db_column='PRVCFAXACR')
    PRVCTIPOAC = models.CharField(max_length=2, blank=True, null=True, db_column='PRVCTIPOAC')
    PRVCGIROAC = models.CharField(max_length=2, blank=True, null=True, db_column='PRVCGIROAC')
    PRVCREPRES = models.CharField(max_length=40, blank=True, null=True, db_column='PRVCREPRES')
    PRVCCARREP = models.CharField(max_length=20, blank=True, null=True, db_column='PRVCCARREP')
    PRVCTELREP = models.CharField(max_length=15, blank=True, null=True, db_column='PRVCTELREP')
    PRVDFECCRE = models.DateTimeField(blank=True, null=True, db_column='PRVDFECCRE')
    PRVCUSER = models.CharField(max_length=8, blank=True, null=True, db_column='PRVCUSER')
    PRPVCRUC = models.CharField(max_length=11, blank=True, null=True, db_column='PRPVCRUC')
    PRVCRUC = models.CharField(max_length=11, blank=True, null=True, db_column='PRVCRUC')
    PRVCABREVI = models.CharField(max_length=12, blank=True, null=True, db_column='PRVCABREVI')
    PRVCESTADO = models.CharField(max_length=2, blank=True, null=True, db_column='PRVCESTADO')
    PRVDFECMOD = models.DateTimeField(blank=True, null=True, db_column='PRVDFECMOD')
    PRVEMAIL = models.CharField(max_length=50, blank=True, null=True, db_column='PRVEMAIL')
    PRVCODFAB = models.CharField(max_length=1, blank=True, null=True, db_column='PRVCODFAB')
    PRVPAGO = models.CharField(max_length=4, blank=True, null=True, db_column='PRVPAGO')
    PRVFACTOR = models.DecimalField(max_digits=15, decimal_places=6, blank=True, null=True, db_column='PRVFACTOR')
    PRVGLOSA = models.CharField(max_length=255, blank=True, null=True, db_column='PRVGLOSA')
    PRVREPRESENTANTE = models.CharField(max_length=60, blank=True, null=True, db_column='PRVREPRESENTANTE')
    PRVCONTACTO = models.CharField(max_length=60, blank=True, null=True, db_column='PRVCONTACTO')
    PRVTELREP = models.CharField(max_length=30, blank=True, null=True, db_column='PRVTELREP')
    PRVFAXREP = models.CharField(max_length=30, blank=True, null=True, db_column='PRVFAXREP')
    PRVEMAILREP = models.CharField(max_length=60, blank=True, null=True, db_column='PRVEMAILREP')
    PRVCTIPO_DOCUMENTO = models.CharField(max_length=2, blank=True, null=True, db_column='PRVCTIPO_DOCUMENTO')
    PRVCAPELLIDO_PATERNO = models.CharField(max_length=20, blank=True, null=True, db_column='PRVCAPELLIDO_PATERNO')
    PRVCAPELLIDO_MATERNO = models.CharField(max_length=20, blank=True, null=True, db_column='PRVCAPELLIDO_MATERNO')
    PRVCPRIMER_NOMBRE = models.CharField(max_length=20, blank=True, null=True, db_column='PRVCPRIMER_NOMBRE')
    PRVCSEGUNDO_NOMBRE = models.CharField(max_length=20, blank=True, null=True, db_column='PRVCSEGUNDO_NOMBRE')
    PRVCDOCIDEN = models.CharField(max_length=15, blank=True, null=True, db_column='PRVCDOCIDEN')
    FLGPORTAL_PROVEEDOR = models.BooleanField(blank=True, null=True, db_column='FLGPORTAL_PROVEEDOR')
    FEC_INACTIVO_BLOQUEADO = models.DateTimeField(blank=True, null=True, db_column='FEC_INACTIVO_BLOQUEADO')
    COD_AUDITORIA = models.CharField(max_length=12, blank=True, null=True, db_column='COD_AUDITORIA')
    UBIGEO = models.CharField(max_length=12, blank=True, null=True, db_column='UBIGEO')

    class Meta:
        db_table = 'MAEPROV'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        managed = False

    def __str__(self):
        return self.prvcnombre or self.prvccodigo


#TABLAS CREADAS EN MYSQL

class Empresa(BaseModel):

    nombre_empresa = models.CharField('Nombre bd', max_length=255)
    razon_social = models.CharField('Razón Social', max_length=255, null=True, blank=True )
    ruc = models.CharField('RUC',max_length=11, null=True,blank=True)

    class Meta:
        db_table = 'empresa'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.razon_social or self.nombre_empresa

class Producto(BaseModel):

    # --- ¡NUEVO CAMPO DE RELACIÓN! ---
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='productos',
        verbose_name='Empresa Propietaria',
        null=True,
        blank=True
    )
    nombre_producto = models.CharField(max_length=255)
    codigo_producto = models.CharField(max_length=255)
    proveedor_marca = models.CharField(max_length=255)



    class Meta:
        db_table = 'producto'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        return self.nombre_producto

class ProveedorTransporte(models.Model):
    nombre_proveedor = models.CharField(max_length=255)
    fecha_de_creacion = models.DateTimeField(auto_now_add=True)
    fecha_de_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'proveedor'

    def __str__(self):
        return self.nombre_proveedor

class Transportista(models.Model):
    nombre_transportista = models.CharField(max_length=255)
    fecha_de_creacion = models.DateTimeField(auto_now_add=True)
    fecha_de_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transportista'

    def __str__(self):
        return self.nombre_transportista

class OrdenCompra(models.Model):
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    numero_oc = models.CharField(max_length=50, unique=True)
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    precio_producto = models.DecimalField(max_digits=10, decimal_places=3)  # Precio definido en la orden
    cantidad = models.PositiveIntegerField(null=True, blank=True,default=0)
    fecha_de_creacion = models.DateTimeField(auto_now_add=True)
    fecha_de_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orden_compra'

    def __str__(self):
        return self.numero_oc

class Despacho(models.Model):
    proveedor = models.ForeignKey(ProveedorTransporte, on_delete=models.CASCADE)
    dua = models.CharField(max_length=50)
    fecha_numeracion = models.DateTimeField()
    carta_porte = models.CharField(max_length=50, blank=True, null=True)
    num_factura = models.CharField(max_length=50)
    transportista = models.ForeignKey(Transportista, on_delete=models.CASCADE)
    flete_pactado = models.DecimalField(max_digits=10, decimal_places=2)
    peso_neto_crt = models.DecimalField(max_digits=10, decimal_places=2)
    ordenes_compra = models.ManyToManyField('OrdenCompra', through='OrdenCompraDespacho', related_name='despachos')
    fecha_llegada = models.DateTimeField(null=True)
    fecha_de_creacion = models.DateTimeField(auto_now_add=True)
    fecha_de_actualizacion = models.DateTimeField(auto_now=True)
    archivo_pdf = models.BinaryField(blank=True, null=True)

    class Meta:
        db_table = 'despacho'

    def __str__(self):
        return f"Despacho {self.id}"

class OrdenCompraDespacho(models.Model):
    despacho = models.ForeignKey(
        'Despacho',
        on_delete=models.CASCADE,
        related_name='ordenes_despacho'  # 🔹 Agregar related_name
    )
    orden_compra = models.ForeignKey('OrdenCompra', on_delete=models.CASCADE)
    cantidad_asignada = models.PositiveIntegerField()
    numero_recojo = models.PositiveIntegerField()
    fecha_de_creacion = models.DateTimeField(auto_now_add=True)
    fecha_de_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orden_compra_despacho'
        unique_together = ('orden_compra', 'numero_recojo')

    def __str__(self):
        return f"Despacho {self.despacho.id} - OC {self.orden_compra.numero_oc} - Recojo {self.numero_recojo}"

class DetalleDespacho(models.Model):
    despacho = models.ForeignKey(Despacho, on_delete=models.CASCADE)
    sacos_cargados = models.IntegerField()
    placa_salida = models.CharField(max_length=10)
    peso_salida = models.DecimalField(max_digits=10, decimal_places=2)
    placa_llegada = models.CharField(max_length=10)
    sacos_descargados = models.IntegerField()
    peso_llegada = models.DecimalField(max_digits=10, decimal_places=2)
    merma = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    sacos_faltantes = models.IntegerField(blank=True, null=True)
    sacos_rotos = models.IntegerField(blank=True, null=True)
    sacos_humedos = models.IntegerField(blank=True, null=True)
    sacos_mojados = models.IntegerField(blank=True, null=True)
    pago_estiba = models.CharField(max_length=50, blank=True, null=True)
    cant_desc = models.IntegerField(blank=True, null=True)
    fecha_de_creacion = models.DateTimeField(auto_now_add=True)
    fecha_de_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'detalle_despacho'

    def __str__(self):
        return f"Detalle {self.id} - Vehículo {self.placa_salida}"

class ConfiguracionDespacho(models.Model):
    despacho = models.ForeignKey(Despacho, on_delete=models.CASCADE)
    merma_permitida = models.DecimalField(max_digits=10, decimal_places=2)
    precio_prod = models.DecimalField(max_digits=10, decimal_places=5)
    gastos_nacionalizacion = models.DecimalField(max_digits=10, decimal_places=2)
    margen_financiero = models.DecimalField(max_digits=10, decimal_places=2)
    precio_sacos_rotos = models.DecimalField(max_digits=10, decimal_places=2)
    precio_sacos_humedos = models.DecimalField(max_digits=10, decimal_places=2)
    precio_sacos_mojados = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_cambio_desc_ext = models.DecimalField(max_digits=10, decimal_places=3)
    precio_estiba= models.DecimalField(max_digits=10, decimal_places=2,null=True)
    fecha_de_creacion = models.DateTimeField(auto_now_add=True)
    fecha_de_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_despacho'

    def __str__(self):
        return f"Configuración para Despacho {self.despacho.id}"

class GastosExtra(models.Model):
    despacho = models.ForeignKey(Despacho, on_delete=models.CASCADE)
    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_de_creacion = models.DateTimeField(auto_now_add=True)
    fecha_de_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gastos_extra'

    def __str__(self):
        return f"Gastos extra del despacho {self.despacho.id}"

def ruta_documento(instance, filename):
    carpeta = "documentos/sin_clasificar"

    try:
        if isinstance(instance.content_object, Declaracion):
            numero = instance.content_object.numero
            anio = instance.content_object.anio
            carpeta = f"documentos/docs_duas/{numero}-{anio}"

        elif isinstance(instance.content_object, ExpedienteDeclaracion):
            numero = instance.content_object.declaracion.numero
            anio = instance.content_object.declaracion.anio
            carpeta = f"documentos/expedientes/{numero}-{anio}"

    except Exception as e:
        # Esto ayuda si estás en modo debug
        print(f"Error obteniendo ruta del documento: {e}")

    return os.path.join(carpeta, filename)


class Declaracion(BaseModel):
    numero = models.CharField(max_length=50)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    anio = models.PositiveIntegerField(blank=True, null=True)
    documentos = GenericRelation('importaciones.Documento')

    class Meta:
        db_table = 'declaracion'
        unique_together = ('numero', 'anio')

    def save(self, *args, **kwargs):
        if self.numero:
            self.numero = self.numero.lstrip('0')
        super().save(*args, **kwargs)

class Documento(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Puedes mantener este mientras haces la transición:
    #declaracion = models.ForeignKey('Declaracion', on_delete=models.CASCADE, related_name='documentos', null=True, blank=True)

    archivo = models.FileField(upload_to=ruta_documento)
    nombre_original = models.CharField(max_length=255)
    hash_archivo = models.CharField(max_length=64, blank=True, null=True)
    referencia_interna = models.CharField(max_length=100, blank=True, null=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.hash_archivo and self.archivo:
            sha256 = hashlib.sha256()
            for chunk in self.archivo.chunks():
                sha256.update(chunk)
            self.hash_archivo = sha256.hexdigest()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'documento'
        indexes = [models.Index(fields=['hash_archivo'])]

    def __str__(self):
        return self.nombre_original

class TipoDocumento(BaseModel):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    uso_interno = models.BooleanField(default=True)  # True = usado por personal interno, False = para proveedor

    class Meta:
        db_table = 'tipo_documento'
        verbose_name = 'Tipo de Documento'
        verbose_name_plural = 'Tipos de Documentos'

    def __str__(self):
        return self.nombre

class ExpedienteDeclaracion(BaseModel):
    declaracion = models.ForeignKey(Declaracion, on_delete=models.CASCADE, related_name='expedientes')
    documento = models.ForeignKey(
        Documento, on_delete=models.CASCADE, related_name='expedientes', null=True, blank=True
    )
    descripcion = models.TextField(blank=True, null=True)
    tipo = models.ForeignKey(TipoDocumento, on_delete=models.SET_NULL, null=True, blank=True,related_name='expedientes')
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    anio_fiscal = models.PositiveIntegerField(null=True, blank=True)
    mes_fiscal = models.PositiveIntegerField(null=True, blank=True)
    folio = models.CharField(max_length=100, blank=True, null=True)
    empresa = models.CharField(max_length=255, blank=True, null=True)
    nota_ingreso = models.CharField(max_length=10, blank=True, null=True)
    orden_compra = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        db_table = 'expediente_declaracion'
        ordering = ['-fecha']

    def __str__(self):
        declaracion_str = str(self.declaracion) if self.declaracion else "Sin declaración"
        documento_str = self.documento.nombre_original if self.documento and self.documento.nombre_original else "Sin documento"
        return f"Expediente de {declaracion_str} - {documento_str}"





