from django.db import models, transaction
from django.db.models import Sum, F, Q, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
import base.models
from importaciones.models import Empresa,Producto
import logging
import datetime

from semilla360 import settings

logger = logging.getLogger(__name__)


#TABLAS EN ERP STARSOFT
class GremisionCab(models.Model):
    serie = models.CharField(db_column='GRENUMSER', max_length=4,primary_key=True)
    numero = models.CharField(db_column='GRENUMDOC', max_length=8)
    tipo_origen = models.CharField(db_column='GRETIPO_ORIGEN', max_length=2)
    fecha_emision = models.DateTimeField(db_column='GREFECEMISION', null=True, blank=True)
    estado = models.CharField(db_column='GRESTADO', max_length=50)
    motivo_traslado = models.CharField(db_column='DESCMOTIVOTRASLADO', max_length=1000)
    emisorrazsocial = models.CharField(db_column='EMISORRAZSOCIAL', max_length=100)
    receptorrazsocial = models.CharField(db_column='RECEPTORRAZSOCIAL', max_length=100)
    transportistarazsocial = models.CharField(db_column='TRANSPORTISTARAZSOCIAL', max_length=100)
    ruc_transportista = models.CharField(db_column='TRANSPORTISTANUMDOC', max_length=15)
    llegada_ubigeo = models.CharField(db_column='LLEGADAUBIGEO', max_length=8)
    llegada_direccion = models.CharField(db_column='LLEGADADIRECCION', max_length=500)
    partida_ubigeo = models.CharField(db_column='PARTIDAUBIGEO', max_length=8)
    partida_direccion = models.CharField(db_column='PARTIDADIRECCION', max_length=500)
    pesobrutototal = models.DecimalField(db_column='PESOBRUTOTOTAL', max_digits=12, decimal_places=3)
    url = models.CharField(db_column='URL_CDR', max_length=1000)

    class Meta:
        managed = False  # Django no crea/borra la tabla
        db_table = 'GREMISION_CAB'
        unique_together = (('serie', 'numero', 'tipo_origen'),)


class GremisionDet(models.Model):
    grenumser = models.CharField(max_length=4, db_column="GRENUMSER",primary_key=True)
    grenumdoc = models.CharField(max_length=8, db_column="GRENUMDOC")
    gretipo = models.CharField(max_length=2, db_column="GRETIPO")
    gretipo_origen = models.CharField(max_length=2, db_column="GRETIPO_ORIGEN")
    itemorden = models.IntegerField(db_column="ITEMORDEN")
    itemcodigo = models.CharField(max_length=50, null=True, blank=True, db_column="ITEMCODIGO")
    itemdescripcion = models.CharField(max_length=250, db_column="ITEMDESCRIPCION")
    itemcantidad = models.DecimalField(max_digits=23, decimal_places=10, default=0, db_column="ITEMCANTIDAD")
    itemumedida = models.CharField(max_length=4, db_column="ITEMUMEDIDA")
    itemumedida_origen = models.CharField(max_length=12, db_column="ITEMUMEDIDA_ORIGEN")


    class Meta:
        managed = False   # Django no crea/borra la tabla
        db_table = "GREMISION_DET"
        unique_together = ("grenumser", "grenumdoc", "gretipo_origen", "itemorden")


class MovAlmCab(models.Model):
    # --- Clave Primaria Compuesta (Hack de Django) ---
    # 1. PK_MOVALMCAB: (CAALMA, CATD, CANUMDOC)
    caalma = models.CharField(primary_key=True, max_length=2, db_column='CAALMA')
    catd = models.CharField(max_length=2, db_column='CATD')
    canumdoc = models.CharField(max_length=11, db_column='CANUMDOC')
    # --------------------------------------------------

    cafecdoc = models.DateTimeField(db_column='CAFECDOC', null=True, blank=True)
    catipmov = models.CharField(max_length=1, db_column='CATIPMOV', null=True, blank=True)
    cacodmov = models.CharField(max_length=2, db_column='CACODMOV', null=True, blank=True)
    casitua = models.CharField(max_length=1, db_column='CASITUA', null=True, blank=True)
    carftdoc = models.CharField(max_length=2, db_column='CARFTDOC', null=True, blank=True)
    carfndoc = models.CharField(max_length=21, db_column='CARFNDOC', null=True, blank=True)
    casoli = models.CharField(max_length=3, db_column='CASOLI', null=True, blank=True)
    cafecdev = models.CharField(max_length=8, db_column='CAFECDEV', null=True, blank=True)
    cacodpro = models.CharField(max_length=11, db_column='CACODPRO', null=True, blank=True)
    cacencos = models.CharField(max_length=10, db_column='CACENCOS', null=True, blank=True)
    carfalma = models.CharField(max_length=2, db_column='CARFALMA', null=True, blank=True)
    caglosa = models.CharField(max_length=8000, db_column='CAGLOSA', null=True, blank=True)
    cafecact = models.DateTimeField(db_column='CAFECACT', null=True, blank=True)
    cahora = models.CharField(max_length=8, db_column='CAHORA', null=True, blank=True)
    causuari = models.CharField(max_length=8, db_column='CAUSUARI', null=True, blank=True)
    cacodcli = models.CharField(max_length=11, db_column='CACODCLI', null=True, blank=True)
    caruc = models.CharField(max_length=11, db_column='CARUC', null=True, blank=True)
    canomcli = models.CharField(max_length=100, db_column='CANOMCLI', null=True, blank=True)
    caforven = models.CharField(max_length=4, db_column='CAFORVEN', null=True, blank=True)
    cacodmon = models.CharField(max_length=2, db_column='CACODMON', default='', blank=True)
    cavende = models.CharField(max_length=2, db_column='CAVENDE', null=True, blank=True)
    catipcam = models.DecimalField(max_digits=15, decimal_places=6, db_column='CATIPCAM', null=True, blank=True,
                                   default=0)
    catipgui = models.CharField(max_length=2, db_column='CATIPGUI', null=True, blank=True)
    casitgui = models.CharField(max_length=1, db_column='CASITGUI', null=True, blank=True)
    caguifac = models.CharField(max_length=1, db_column='CAGUIFAC', null=True, blank=True)
    cadirenv = models.CharField(max_length=100, db_column='CADIRENV', null=True, blank=True)
    cacodtran = models.CharField(max_length=11, db_column='CACODTRAN', null=True, blank=True)
    canumord = models.CharField(max_length=5000, db_column='CANUMORD', null=True, blank=True)
    caguidev = models.CharField(max_length=1, db_column='CAGUIDEV', null=True, blank=True)
    canompro = models.CharField(max_length=100, db_column='CANOMPRO', null=True, blank=True)
    canroped = models.CharField(max_length=5000, db_column='CANROPED', null=True, blank=True)
    cacotiza = models.CharField(max_length=10, db_column='CACOTIZA', null=True, blank=True)
    capordescl = models.DecimalField(max_digits=15, decimal_places=6, db_column='CAPORDESCL', null=True, blank=True,
                                     default=0)
    capordeses = models.DecimalField(max_digits=15, decimal_places=6, db_column='CAPORDESES', null=True, blank=True,
                                     default=0)
    caimporte = models.DecimalField(max_digits=15, decimal_places=6, db_column='CAIMPORTE', null=True, blank=True,
                                    default=0)
    canomtra = models.CharField(max_length=40, db_column='CANOMTRA', null=True, blank=True)
    cadirtra = models.CharField(max_length=50, db_column='CADIRTRA', null=True, blank=True)
    caructra = models.CharField(max_length=11, db_column='CARUCTRA', null=True, blank=True)
    caplatra = models.CharField(max_length=10, db_column='CAPLATRA', null=True, blank=True)
    canroimp = models.CharField(max_length=13, db_column='CANROIMP', null=True, blank=True)
    cacodliq = models.CharField(max_length=20, db_column='CACODLIQ', null=True, blank=True)
    caestimp = models.CharField(max_length=1, db_column='CAESTIMP', null=True, blank=True)
    cierre = models.BooleanField(db_column='CACIERRE', default=0)
    catipdep = models.CharField(max_length=2, db_column='CATIPDEP', null=True, blank=True)
    cazonaf = models.CharField(max_length=2, db_column='CAZONAF', null=True, blank=True)
    flaggs = models.BooleanField(db_column='FLAGGS', default=0)
    asiento = models.BooleanField(db_column='ASIENTO', default=0)
    caflete = models.DecimalField(max_digits=15, decimal_places=6, db_column='CAFLETE', null=True, blank=True,
                                  default=0)
    caordfab = models.CharField(max_length=5000, db_column='CAORDFAB', null=True, blank=True)
    capedrefe = models.CharField(max_length=13, db_column='CAPEDREFE', null=True, blank=True)
    caimportacion = models.BooleanField(db_column='CAIMPORTACION', null=True, default=0)
    canrocajas = models.IntegerField(db_column='CANROCAJAS', default=0)
    capesototal = models.DecimalField(max_digits=15, decimal_places=6, db_column='CAPESOTOTAL', default=0)
    cadespacho = models.BooleanField(db_column='CADESPACHO', default=0)
    linvcodigo = models.CharField(max_length=2, db_column='LINVCODIGO', null=True, blank=True)
    cod_direccion = models.DecimalField(max_digits=9, decimal_places=0, db_column='COD_DIRECCION', null=True,
                                        blank=True)
    costomin = models.DecimalField(max_digits=15, decimal_places=6, db_column='COSTOMIN', null=True, blank=True,
                                   default=0)
    cainterface = models.IntegerField(db_column='CAINTERFACE', null=True, blank=True, default=0)
    cactacont = models.CharField(max_length=18, db_column='CACTACONT', null=True, blank=True)
    cacontrolstock = models.CharField(max_length=1, db_column='CACONTROLSTOCK', default='N')
    canomrecep = models.CharField(max_length=70, db_column='CANOMRECEP', null=True, blank=True)
    cadnirecep = models.CharField(max_length=8, db_column='CADNIRECEP', null=True, blank=True)
    cfdirerefe = models.CharField(max_length=150, db_column='CFDIREREFE', null=True, blank=True)
    reg_compra = models.BooleanField(db_column='REG_COMPRA', null=True)
    oc_ni_guia = models.BooleanField(db_column='OC_NI_GUIA', default=0)
    cod_auditoria = models.CharField(max_length=12, db_column='COD_AUDITORIA', null=True, blank=True)
    cod_modulo = models.CharField(max_length=2, db_column='COD_MODULO', null=True, blank=True)
    no_giro_negocio = models.BooleanField(db_column='NO_GIRO_NEGOCIO', default=0)
    motivo_anulacion_doc_electronico = models.CharField(max_length=100, db_column='MOTIVO_ANULACION_DOC_ELECTRONICO',
                                                        null=True, blank=True)
    documento_electronico = models.BooleanField(db_column='DOCUMENTO_ELECTRONICO', null=True)
    gs_baja = models.CharField(max_length=15, db_column='GS_BAJA', null=True, blank=True)
    flg_gs_baja = models.BooleanField(db_column='FLG_GS_BAJA', null=True)
    cadocumentoimportado = models.CharField(max_length=12, db_column='CADocumentoImportado', null=True, blank=True)
    documento_contingencia = models.BooleanField(db_column='DOCUMENTO_CONTINGENCIA', null=True)
    ge_baja = models.CharField(max_length=11, db_column='GE_BAJA', null=True, blank=True)
    solicitante = models.CharField(max_length=100, db_column='SOLICITANTE', null=True, blank=True)
    etiqueta1 = models.CharField(max_length=100, db_column='ETIQUETA1', null=True, blank=True)
    etiqueta2 = models.CharField(max_length=100, db_column='ETIQUETA2', null=True, blank=True)
    etiqueta3 = models.CharField(max_length=100, db_column='ETIQUETA3', null=True, blank=True)
    etiqueta4 = models.CharField(max_length=100, db_column='ETIQUETA4', null=True, blank=True)
    etiqueta5 = models.CharField(max_length=100, db_column='ETIQUETA5', null=True, blank=True)
    etiqueta6 = models.CharField(max_length=100, db_column='ETIQUETA6', null=True, blank=True)
    etiqueta7 = models.CharField(max_length=50, db_column='ETIQUETA7', null=True, blank=True)
    etiqueta8 = models.CharField(max_length=100, db_column='ETIQUETA8', null=True, blank=True)
    gs_transportista = models.BooleanField(db_column='GS_TRANSPORTISTA', null=True)
    cafectras = models.DateTimeField(db_column='CAFECTRAS', null=True, blank=True)
    motivo_gs = models.CharField(max_length=50, db_column='MOTIVO_GS', null=True, blank=True)
    direcion_prov = models.CharField(max_length=100, db_column='DIRECION_PROV', null=True, blank=True)
    comentario = models.CharField(max_length=500, db_column='COMENTARIO', null=True, blank=True)
    cantbultos = models.CharField(max_length=20, db_column='CANTBULTOS', null=True, blank=True)
    numctn1 = models.CharField(max_length=20, db_column='NUMCTN1', null=True, blank=True)
    numpto1 = models.CharField(max_length=20, db_column='NUMPTO1', null=True, blank=True)
    numctn2 = models.CharField(max_length=20, db_column='NUMCTN2', null=True, blank=True)
    numpto2 = models.CharField(max_length=20, db_column='NUMPTO2', null=True, blank=True)
    cod_direccionp = models.DecimalField(max_digits=9, decimal_places=0, db_column='COD_DIRECCIONP', null=True,
                                         blank=True)
    codpuertodesembarque = models.CharField(max_length=3, db_column='CODPUERTODESEMBARQUE', null=True, blank=True)
    nompuertodesembarque = models.CharField(max_length=250, db_column='NOMPUERTODESEMBARQUE', null=True, blank=True)
    numregmtc = models.CharField(max_length=20, db_column='NUMREGMTC', null=True, blank=True)
    flgdesde_transportista = models.BooleanField(db_column='FLGDESDE_TRANSPORTISTA', null=True)
    cliente_tercero = models.CharField(max_length=11, db_column='CLIENTE_TERCERO', null=True, blank=True)
    direccion_tercero = models.CharField(max_length=100, db_column='DIRECCION_TERCERO', null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'MOVALMCAB'
        # 2. Definir la PK Compuesta
        unique_together = (('caalma', 'catd', 'canumdoc'),)

    def __str__(self):
        return f"{self.caalma}-{self.catd}-{self.canumdoc}"


class MovAlmDet(models.Model):
    # --- Clave Primaria Compuesta (Hack de Django) ---
    # 1. PK_MOVALMDET: (DEALMA, DETD, DENUMDOC, DEITEM)
    dealma = models.CharField(primary_key=True, max_length=2, db_column='DEALMA')
    detd = models.CharField(max_length=2, db_column='DETD')
    denumdoc = models.CharField(max_length=11, db_column='DENUMDOC')
    deitem = models.IntegerField(db_column='DEITEM')
    # --------------------------------------------------

    decodigo = models.CharField(max_length=20, db_column='DECODIGO', null=True, blank=True)
    decodref = models.CharField(max_length=40, db_column='DECODREF', null=True, blank=True)
    decantid = models.DecimalField(max_digits=15, decimal_places=6, db_column='DECANTID', null=True, blank=True,
                                   default=0)
    decantent = models.DecimalField(max_digits=15, decimal_places=6, db_column='DECANTENT', null=True, blank=True,
                                    default=0)
    decanref = models.DecimalField(max_digits=15, decimal_places=6, db_column='DECANREF', null=True, blank=True,
                                   default=0)
    decanfac = models.DecimalField(max_digits=15, decimal_places=6, db_column='DECANFAC', null=True, blank=True,
                                   default=0)
    deorden = models.CharField(max_length=6, db_column='DEORDEN', null=True, blank=True)
    depreuni = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEPREUNI', null=True, blank=True,
                                   default=0)
    deprecio = models.DecimalField(max_digits=28, decimal_places=6, db_column='DEPRECIO', null=True, blank=True,
                                   default=0)
    depreci1 = models.DecimalField(max_digits=28, decimal_places=6, db_column='DEPRECI1', null=True, blank=True,
                                   default=0)
    dedescto = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEDESCTO', null=True, blank=True,
                                   default=0)
    destock = models.CharField(max_length=50, db_column='DESTOCK', null=True, blank=True)
    deigv = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEIGV', null=True, blank=True, default=0)
    deimpmn = models.DecimalField(max_digits=28, decimal_places=6, db_column='DEIMPMN', null=True, blank=True,
                                  default=0)
    deimpus = models.DecimalField(max_digits=28, decimal_places=6, db_column='DEIMPUS', null=True, blank=True,
                                  default=0)
    deserie = models.CharField(max_length=45, db_column='DESERIE', null=True, blank=True)
    desitua = models.CharField(max_length=1, db_column='DESITUA', null=True, blank=True)
    defecdoc = models.DateTimeField(db_column='DEFECDOC', null=True, blank=True)
    decencos = models.CharField(max_length=10, db_column='DECENCOS', null=True, blank=True)
    derfalma = models.CharField(max_length=2, db_column='DERFALMA', null=True, blank=True)
    detr = models.CharField(max_length=1, db_column='DETR', null=True, blank=True)
    deestado = models.CharField(max_length=1, db_column='DEESTADO', null=True, blank=True)
    decodmov = models.CharField(max_length=2, db_column='DECODMOV', null=True, blank=True)
    devaltot = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEVALTOT', null=True, blank=True,
                                   default=0)
    decompro = models.CharField(max_length=6, db_column='DECOMPRO', null=True, blank=True)
    decodmon = models.CharField(max_length=2, db_column='DECODMON', null=True, blank=True)
    detipo = models.CharField(max_length=1, db_column='DETIPO', null=True, blank=True)
    detipcam = models.DecimalField(max_digits=15, decimal_places=6, db_column='DETIPCAM', null=True, blank=True,
                                   default=0)
    deprevta = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEPREVTA', null=True, blank=True,
                                   default=0)
    demonvta = models.CharField(max_length=2, db_column='DEMONVTA', null=True, blank=True)
    defecven = models.DateTimeField(db_column='DEFECVEN', null=True, blank=True)
    dedevol = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEDEVOL', null=True, blank=True,
                                  default=0)
    desoli = models.CharField(max_length=3, db_column='DESOLI', null=True, blank=True)
    dedescri = models.CharField(max_length=200, db_column='DEDESCRI', null=True, blank=True)
    depordes = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEPORDES', null=True, blank=True,
                                   default=0)
    deigvpor = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEIGVPOR', null=True, blank=True,
                                   default=0)
    dedescli = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEDESCLI', null=True, blank=True,
                                   default=0)
    dedesesp = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEDESESP', null=True, blank=True,
                                   default=0)
    denumfac = models.CharField(max_length=10, db_column='DENUMFAC', null=True, blank=True)
    delote = models.CharField(max_length=45, db_column='DELOTE', null=True, blank=True)
    deunidad = models.CharField(max_length=6, db_column='DEUNIDAD', null=True, blank=True)
    decantbruta = models.DecimalField(max_digits=15, decimal_places=6, db_column='DECANTBRUTA', null=True, blank=True,
                                      default=0)
    dedsctcantbruta = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEDSCTCANTBRUTA', null=True,
                                          blank=True, default=0)
    deordfab = models.CharField(max_length=20, db_column='DEORDFAB', null=True, blank=True)
    dequipo = models.CharField(max_length=10, db_column='DEQUIPO', null=True, blank=True)
    deflete = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEFLETE', null=True, blank=True,
                                  default=0)
    deitemi = models.CharField(max_length=10, db_column='DEITEMI', null=True, blank=True)
    deglosa = models.CharField(max_length=300, db_column='DEGLOSA', null=True, blank=True)
    devalorizado = models.BooleanField(db_column='DEVALORIZADO', default=0)
    desecuenori = models.CharField(max_length=3, db_column='DESECUENORI', null=True, blank=True)
    dereferencia = models.CharField(max_length=5000, db_column='DEREFERENCIA', null=True, blank=True)
    umreferencia = models.CharField(max_length=6, db_column='UMREFERENCIA', null=True, blank=True)
    cantreferencia = models.DecimalField(max_digits=15, decimal_places=6, db_column='CANTREFERENCIA', null=True,
                                         blank=True, default=0)
    decuenta = models.CharField(max_length=18, db_column='DECUENTA', null=True, blank=True)
    detexto = models.TextField(db_column='DETEXTO', null=True, blank=True)
    cta_consumo = models.CharField(max_length=18, db_column='CTA_CONSUMO', null=True, blank=True)
    codparte = models.CharField(max_length=3, db_column='CODPARTE', default='')
    codplano = models.CharField(max_length=3, db_column='CODPLANO', default='')
    detproduccion = models.IntegerField(db_column='DETPRODUCCION', default=0)
    mpma = models.CharField(max_length=2, db_column='MPMA', default='')
    porcentajecosto = models.DecimalField(max_digits=28, decimal_places=6, db_column='PorcentajeCosto', default=0)
    deprecioref = models.DecimalField(max_digits=28, decimal_places=6, db_column='DEPRECIOREF', null=True, blank=True,
                                      default=0)
    saldo_nc = models.DecimalField(max_digits=18, decimal_places=6, db_column='SALDO_NC', null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'MOVALMDET'
        # 2. Definir la PK Compuesta
        unique_together = (('dealma', 'detd', 'denumdoc', 'deitem'),)

    def __str__(self):
        return f"{self.dealma}-{self.detd}-{self.denumdoc} (Item: {self.deitem})"

#FIN TABLAS EN ERP STARSOFT

class LegacyMovAlmCab(models.Model):
    """
    Copia 1:1 (en MySQL) de la tabla MOVALMCAB de SQL Server.
    La 'empresa' nos dice de qué BD del ERP vino.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='legacy_cabeceras')

    # --- Campos 1:1 de MOVALMCAB ---
    # Usamos la misma definición de tus modelos managed=False
    caalma = models.CharField(max_length=2, db_column='CAALMA')
    catd = models.CharField(max_length=2, db_column='CATD')
    canumdoc = models.CharField(max_length=11, db_column='CANUMDOC')

    cafecdoc = models.DateTimeField(db_column='CAFECDOC', null=True, blank=True)
    catipmov = models.CharField(max_length=1, db_column='CATIPMOV', null=True, blank=True)
    cacodmov = models.CharField(max_length=2, db_column='CACODMOV', null=True, blank=True)
    casitua = models.CharField(max_length=1, db_column='CASITUA', null=True, blank=True)
    carftdoc = models.CharField(max_length=2, db_column='CARFTDOC', null=True, blank=True)
    carfndoc = models.CharField(max_length=21, db_column='CARFNDOC', null=True, blank=True)
    casoli = models.CharField(max_length=3, db_column='CASOLI', null=True, blank=True)
    cafecdev = models.CharField(max_length=8, db_column='CAFECDEV', null=True, blank=True)
    cacodpro = models.CharField(max_length=11, db_column='CACODPRO', null=True, blank=True)
    cacencos = models.CharField(max_length=10, db_column='CACENCOS', null=True, blank=True)
    carfalma = models.CharField(max_length=2, db_column='CARFALMA', null=True, blank=True)
    caglosa = models.CharField(max_length=8000, db_column='CAGLOSA', null=True, blank=True)
    cafecact = models.DateTimeField(db_column='CAFECACT', null=True, blank=True)
    cahora = models.CharField(max_length=8, db_column='CAHORA', null=True, blank=True)
    causuari = models.CharField(max_length=8, db_column='CAUSUARI', null=True, blank=True)
    cacodcli = models.CharField(max_length=11, db_column='CACODCLI', null=True, blank=True)
    canomcli = models.CharField(max_length=100, db_column='CANOMCLI', null=True, blank=True)
    casitgui = models.CharField(max_length=1, db_column='CASITGUI', null=True, blank=True)
    canompro = models.CharField(max_length=100, db_column='CANOMPRO', null=True, blank=True)
    canomtra = models.CharField(max_length=40, db_column='CANOMTRA', null=True, blank=True)
    cacodtran = models.CharField(max_length=11, db_column='CACODTRAN', null=True, blank=True)
    caimportacion = models.BooleanField(db_column='CAIMPORTACION', null=True, default=0)
    canroimp = models.CharField(max_length=13, db_column='CANROIMP', null=True, blank=True)
    motivo_gs = models.CharField(max_length=50, db_column='MOTIVO_GS', null=True, blank=True)
    canumord = models.CharField(max_length=5000, db_column='CANUMORD', null=True, blank=True)
    cadirenv= models.TextField( db_column='CADIRENV', null=True, blank=True)

    # --- Control de Sincronización (Opcional pero recomendado) ---
    # fecha_sincronizado = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True  # Django gestionará esta tabla en MySQL
        db_table = 'legacy_movalmcab'
        verbose_name = 'ERP Legacy Cabecera'
        verbose_name_plural = 'ERP Legacy Cabeceras'
        # Clave única para evitar duplicados en nuestra BD
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'caalma', 'catd', 'canumdoc'], name='unique_legacy_cab_pk')
        ]
        indexes = [
            models.Index(fields=['empresa', 'cafecdoc']),  # Para buscar por fecha
        ]


class LegacyMovAlmDet(models.Model):
    """
    Copia 1:1 (en MySQL) de la tabla MOVALMDET de SQL Server.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='legacy_detalles')

    # --- Relación con la Cabecera (opcional, pero útil) ---
    # Descomentar si queremos vincularlas, aunque podemos usar los campos clave
    # legacy_cab = models.ForeignKey(LegacyMovAlmCab, on_delete=models.CASCADE, related_name='detalles')

    # --- Campos 1:1 de MOVALMDET ---
    dealma = models.CharField(max_length=2, db_column='DEALMA')
    detd = models.CharField(max_length=2, db_column='DETD')
    denumdoc = models.CharField(max_length=11, db_column='DENUMDOC')
    deitem = models.IntegerField(db_column='DEITEM')

    decodigo = models.CharField(max_length=20, db_column='DECODIGO', null=True, blank=True)
    decantid = models.DecimalField(max_digits=15, decimal_places=6, db_column='DECANTID', null=True, blank=True)
    depreuni = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEPREUNI', null=True, blank=True)
    deserie = models.CharField(max_length=45, db_column='DESERIE', null=True, blank=True)
    defecdoc = models.DateTimeField(db_column='DEFECDOC', null=True, blank=True)
    deglosa = models.CharField(max_length=300, db_column='DEGLOSA', null=True, blank=True)
    delote = models.CharField(max_length=45, db_column='DELOTE', null=True, blank=True)
    deunidad = models.CharField(max_length=6, db_column='DEUNIDAD', null=True, blank=True)
    devaltot = models.DecimalField(max_digits=15, decimal_places=6, db_column='DEVALTOT', null=True, blank=True)
    dedescri = models.CharField(max_length=200, db_column='DEDESCRI', null=True, blank=True)
    detexto = models.TextField(db_column='DETEXTO', null=True, blank=True)

    # --- Control de Sincronización (Opcional pero recomendado) ---
    # fecha_sincronizado = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True  # Django gestionará esta tabla en MySQL
        db_table = 'legacy_movalmdet'
        verbose_name = 'ERP Legacy Detalle'
        verbose_name_plural = 'ERP Legacy Detalles'
        # Clave única para evitar duplicados en nuestra BD
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'dealma', 'detd', 'denumdoc', 'deitem'],
                                    name='unique_legacy_det_pk')
        ]
        indexes = [
            models.Index(fields=['empresa', 'dealma', 'detd', 'denumdoc']),  # Para buscar detalles de una cabecera
            models.Index(fields=['empresa', 'decodigo']),  # Para buscar por producto
        ]


class Almacen(base.models.BaseModel):

    # --- ¡NUEVO CAMPO DE RELACIÓN! ---
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE, # Si se borra la empresa, se borran sus almacenes
        related_name='almacenes', # Permite hacer: mi_empresa.almacenes.all()
        verbose_name='Empresa Perteneciente',
        null=True,  # Opcional: ¿Puede un almacén existir sin empresa?
        blank=True  # Opcional: Permite que el campo esté vacío en formularios
    )
    # ----------------------------------

    # --- Tus Campos Originales ---
    codigo = models.CharField(max_length=2)
    descripcion = models.CharField(max_length=25, null=True, blank=True)
    distrito = models.CharField(max_length=30, null=True, blank=True)
    telefono = models.CharField(max_length=10,  null=True, blank=True)
    tactlnum = models.CharField(max_length=1, null=True, blank=True)
    tanument = models.IntegerField(null=True, default=0)
    tanumsal = models.IntegerField(null=True, default=0)
    direccion = models.CharField(max_length=100, null=True, blank=True)
    atipo = models.CharField(max_length=2, null=True, blank=True)
    tipo_almacen = models.CharField(max_length=2, null=True, blank=True)
    ubigeo = models.CharField(max_length=12, null=True, blank=True)
    tacod_establecimiento = models.CharField(max_length=5, null=True, blank=True)

    # --- CAMPO ELIMINADO ---
    # Se quita 'estado' porque 'BaseModel' ya provee el campo 'state'
    # estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'almacen'
        verbose_name = 'Almacén'
        verbose_name_plural = 'Almacenes'

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


class MovimientoAlmacen(base.models.BaseModel):  # Hereda de tu BaseModel
    """
    Representa un movimiento de almacén sincronizado desde el ERP.
    Puede ser una línea de una Nota de Ingreso, Guía de Salida, etc.
    """
    # --- Claves Foráneas a tus modelos principales ---
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='movimientos')
    almacen = models.ForeignKey(Almacen, on_delete=models.CASCADE, related_name='movimientos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='movimientos')

    # --- Identificadores del ERP (¡Vitales!) ---
    # Guardamos las claves compuestas como strings
    id_erp_cab = models.CharField(max_length=50, db_index=True,
                                  help_text="PK de MOVALMCAB (ej: AD-NI-0000001)")
    id_erp_det = models.CharField(max_length=60, db_index=True,
                                  help_text="PK de MOVALMDET (ej: AD-NI-0000001-1)")
    # --- Datos del Movimiento (Mapeados desde ERP) ---
    tipo_documento_erp = models.CharField(max_length=2, help_text="Ej: NI, GS, TR (viene de CATD/DETD)")
    numero_documento_erp = models.CharField(max_length=11, help_text="Ej: 0000001 (viene de CANUMDOC/DENUMDOC)")
    item_erp = models.IntegerField(help_text="Número de línea (viene de DEITEM)")
    fecha_documento = models.DateTimeField()
    fecha_movimiento = models.DateTimeField(null=True, blank=True, help_text="Podría ser CAFECDOC o CAFECACT")
    cantidad = models.DecimalField(max_digits=15, decimal_places=6)
    unidad_medida_erp = models.CharField(max_length=6, null=True, blank=True)
    costo_unitario = models.DecimalField(max_digits=15, decimal_places=6, default=0)
    valor_total = models.DecimalField(max_digits=15, decimal_places=6, default=0)
    glosa_cabecera = models.TextField(null=True, blank=True)
    glosa_detalle = models.TextField(null=True, blank=True)
    referencia_documento = models.CharField(max_length=25, null=True, blank=True)
    numero_orden_compra = models.TextField(null=True, blank=True)  # TextField por CANUMORD(5000)
    lote = models.CharField(max_length=50, null=True, blank=True)
    serie = models.CharField(max_length=50, null=True, blank=True)
    proveedor_erp_id = models.CharField(max_length=15, null=True, blank=True, db_index=True)  # Indexar si buscas por él
    #cliente_erp_id = models.CharField(max_length=15, null=True, blank=True, db_index=True)  # Indexar si buscas por él
    cliente_erp_id = models.CharField(max_length=15, null=True, blank=True, db_index=True, help_text="CACODCLI")
    cliente_erp_nombre = models.CharField(max_length=100, null=True, blank=True, help_text="CANOMCLI")
    direccion_envio_erp = models.CharField(max_length=100, null=True, blank=True, help_text="CADIRENV")
    estado_erp = models.CharField(max_length=1, null=True, blank=True, db_index=True,
                                  help_text="CASITGUI (F=Facturado, V=Venta, A=Anulado)")
    es_ingreso = models.BooleanField(default=True, help_text="True para NI, False para GS/TR")
    motivo_tras = models.CharField(max_length=100, null=True, blank=True, help_text="MOTIVO_GS")
    almacen_ref=models.CharField(max_length=10, null=True, blank=True, help_text="CARFALMA")
    nombre_proveedor=models.CharField(max_length=100, null=True, blank=True, help_text="CANOMPRO")
    id_transportista_erp= models.CharField(max_length=100, null=True, blank=True, help_text="CACODTRAN")
    id_importacion=models.CharField(max_length=20, null=True, blank=True, help_text="CANROIMP")
    importacion=models.BooleanField(default=False,null=True,blank=True,help_text="CAIMPORTACION")
    nombre_transportista=models.CharField(max_length=150, null=True,blank=True, help_text="CANOMTRA")
    codigo_movimiento=models.CharField(max_length=10,null=True,blank=True, help_text="CACODMOV")
    sede_facturacion = models.ForeignKey(
        Almacen,
        on_delete=models.SET_NULL,
        related_name='movimientos_reportados',
        null=True, blank=True,
        help_text="Almacén/Sede para reportes (usado en GV para vincular a sede de factura)"
    )
    cantidad_bultos = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                          help_text="Cantidad de bultos (ej. campo CANTBULTOS del ERP)")

    #sede_afecta=models.CharField(max_length=10,null=True,blank=True,help_text="AQP= AREQUIPA, LM= LIMA, NA= no aplica")
    #estado_mov=models.

    class Meta:
        verbose_name = "Movimiento de Almacén"
        verbose_name_plural = "Movimientos de Almacén"
        # Asegura que no haya duplicados basados en la clave del ERP detalle
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'id_erp_det'],  # La UNICIDAD es la COMBINACIÓN
                name='unique_erp_detail_movement'
            )
        ]

    @property
    def descripcion_visual(self):
        """
        Retorna una descripción formateada inteligentemente para reportes
        basada en el tipo de movimiento, glosas y entidades.
        """
        # Normalizamos el código para evitar errores por mayúsculas/minúsculas o nulos
        cod_mov = self.codigo_movimiento.upper() if self.codigo_movimiento else ""

        # --- CASO 1: TRANSFERENCIAS (TD) ---
        if cod_mov == 'TD':
            # Si hay glosa manual, úsala. Si no, construye el texto standard.
            if self.glosa_cabecera:
                return self.glosa_cabecera

            ref = self.almacen_ref if self.almacen_ref else "DESCONOCIDO"
            return f"TRANSFERENCIA ENTRE ALMACENES - {ref}"

        # --- CASO 2: INGRESO POR FLETE (FT) ---
        elif cod_mov == 'FT' and self.es_ingreso:
            glosa = self.glosa_cabecera if self.glosa_cabecera else ""
            return f"INGRESO POR FLETE - {glosa}"

        # --- CASO 3: NORMAL (Compras, Ventas, Ajustes) ---
        else:
            # Determinamos la entidad (Proveedor o Cliente)
            entidad = self.nombre_proveedor if self.es_ingreso else self.cliente_erp_nombre

            # Limpieza de datos (Evitar 'None' en el texto)
            entidad_str = entidad.strip() if entidad else ""
            glosa_str = self.glosa_cabecera.strip() if self.glosa_cabecera else ""

            # Unimos las partes que existan con un guion
            # filter(None, ...) elimina cadenas vacías de la lista
            partes = filter(None, [entidad_str, glosa_str])
            resultado = " - ".join(partes)

            # Si no hay ni entidad ni glosa, retornamos un fallback
            return resultado if resultado else "Sin detalle registrado"


    def __str__(self):
        tipo = "Entrada" if self.es_ingreso else "Salida"
        return f"{tipo} {self.producto.nombre_producto} ({self.cantidad}) en {self.almacen.codigo} ({self.fecha_documento.date()})"


class MovimientoAlmacenNota(base.models.BaseModel): # Hereda de BaseModel
    """
    Guarda las líneas de detalle del ERP que no son productos
    (ej. DECODIGO='TEXTO'), como glosas o comentarios adicionales.
    """
    # --- Relación con la Empresa ---
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='notas_movimiento')

    # --- Identificadores del ERP ---
    id_erp_cab = models.CharField(max_length=50, db_index=True,
                                  help_text="PK de MOVALMCAB (ej: AD-NI-0000001)")
    id_erp_det = models.CharField(max_length=60, db_index=True,
                                  help_text="PK de MOVALMDET para esta línea de texto (ej: AD-NI-0000001-2)")
    item_erp = models.IntegerField(help_text="Número de línea (viene de DEITEM)")

    # --- Campos de Texto (Mapeados desde ERP) ---
    # Usaremos TextField para asegurar que quepa cualquier longitud
    texto_descripcion = models.TextField(null=True, blank=True, help_text="Viene de DEDESCRI en la línea 'TEXTO'")
    texto_detalle = models.TextField(null=True, blank=True, help_text="Viene de DETEXTO en la línea 'TEXTO'")
    # Puedes añadir otros campos de la línea 'TEXTO' si son relevantes (ej. DEGLOSA)

    # --- Relación Opcional con MovimientoAlmacen (Avanzado) ---
    # Si quisieras vincular esta nota a la cabecera O a una línea específica de producto
    # podrías añadir un ForeignKey a MovimientoAlmacen, pero puede ser complejo.
    # Por ahora, la relación con id_erp_cab es suficiente.

    class Meta:
        verbose_name = "Nota de Movimiento de Almacén"
        verbose_name_plural = "Notas de Movimientos de Almacén"
        # Asegura unicidad por detalle ERP
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'id_erp_det'], name='unique_erp_detail_note')
        ]

    def __str__(self):
        return f"Nota Item {self.item_erp} para Doc: {self.id_erp_cab}"


class Stock(models.Model):
    # ... (tus campos: empresa, almacen, producto, etc.) ...
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='stocks')
    almacen = models.ForeignKey(Almacen, on_delete=models.CASCADE, related_name='stocks')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='stocks')
    cantidad_actual = models.DecimalField(max_digits=15, decimal_places=6, default=0)
    cantidad_en_transito = models.DecimalField(max_digits=15, decimal_places=6, default=0)
    fecha_ultimo_movimiento = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (('empresa', 'almacen', 'producto'),)
        verbose_name = "Stock Actual"
        # ¡IMPORTANTE! Asegúrate de tener los índices que te recomendé para el performance
        indexes = [
            models.Index(fields=['empresa', 'almacen', 'producto']),
        ]

    def __str__(self):
        return f"{self.producto.codigo_producto} en {self.almacen.codigo}: {self.cantidad_actual}"

    # --- ¡AQUÍ DEBE ESTAR EL ERROR! ---
    # Reemplaza tu función con esta:
    @staticmethod
    def recalcular_stock_completo(empresa_id, almacen_id, producto_id):
        """
        Recalcula el stock basándose ÚNICAMENTE en MovimientoAlmacen.
        Lógica: Si está en MovimientoAlmacen, es porque ya afectó el stock físico.
        """

        # 1. Sumar Ingresos y Salidas de MovimientoAlmacen
        agregado = MovimientoAlmacen.objects.filter(
            empresa_id=empresa_id,
            almacen_id=almacen_id,
            producto_id=producto_id,
            state=True
        ).aggregate(
            ingresos=Coalesce(Sum('cantidad', filter=Q(es_ingreso=True)), 0, output_field=DecimalField()),
            salidas=Coalesce(Sum('cantidad', filter=Q(es_ingreso=False)), 0, output_field=DecimalField())
        )

        stock_actual = agregado['ingresos'] - agregado['salidas']

        # 2. Calcular Stock en Tránsito (Solo informativo, no afecta el actual)
        # Viene de las Transferencias que salieron de aquí y siguen EN_TRANSITO
        en_transito = Transferencia.objects.filter(
            empresa_id=empresa_id,
            almacen_origen_id=almacen_id,
            producto_id=producto_id,
            estado='EN_TRANSITO'
        ).aggregate(
            total=Coalesce(Sum('cantidad_enviada'), 0, output_field=DecimalField())
        )['total']

        # 3. Guardar
        Stock.objects.update_or_create(
            empresa_id=empresa_id,
            almacen_id=almacen_id,
            producto_id=producto_id,
            defaults={
                'cantidad_actual': stock_actual,
                'cantidad_en_transito': en_transito
            }
        )


class Transferencia(base.models.BaseModel):
    ESTADOS = [
        ('EN_TRANSITO', 'En Tránsito'),
        ('RECIBIDO', 'Recibido Completo'),
        ('RECIBIDO_PARCIAL', 'Recibido Parcial (Pérdida)'),
        ('RECIBIDO_SOBRANTE', 'Recibido Sobrante (Ganancia)'),
        ('PERDIDO', 'Pérdida Total'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='transferencias')

    # Clave del DETALLE de la GS (Salida)
    id_erp_salida_det = models.CharField(max_length=60, db_index=True)
    # Clave del DETALLE de la NI (Ingreso)
    id_erp_ingreso_det = models.CharField(max_length=60, db_index=True, null=True, blank=True)
    # Guardamos cabeceras para referencia
    id_erp_salida_cab = models.CharField(max_length=50, db_index=True)
    id_erp_ingreso_cab = models.CharField(max_length=50, db_index=True, null=True, blank=True)

    almacen_origen = models.ForeignKey(Almacen, on_delete=models.PROTECT, related_name='transferencias_salientes')
    almacen_destino = models.ForeignKey(Almacen, on_delete=models.PROTECT, related_name='transferencias_entrantes')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='transferencias')

    cantidad_enviada = models.DecimalField(max_digits=15, decimal_places=6)
    cantidad_recibida = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True)
    cantidad_diferencia = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True, default=0)

    estado = models.CharField(max_length=20, choices=ESTADOS, default='EN_TRANSITO', db_index=True)
    fecha_envio = models.DateTimeField(help_text="Fecha del documento de salida (GS)")
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    notas_recepcion = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Transferencia entre Almacenes"
        # La clave única es el DETALLE de salida por empresa
        unique_together = (('empresa', 'id_erp_salida_det'),)
        indexes = [
            models.Index(fields=['empresa', 'almacen_destino', 'producto', 'estado', 'fecha_recepcion']),
            models.Index(fields=['empresa', 'almacen_origen', 'producto', 'estado']),
            models.Index(fields=['empresa', 'id_erp_ingreso_det']),
        ]

    def __str__(self):
        return f"Traslado {self.id_erp_salida_det} ({self.estado})"

    def _disparar_recalculo_stock(self):
        """
        Función helper que se ejecuta DESPUÉS de que la transacción se haya guardado.
        """
        logger.info(f"COMMIT exitoso para {self.id}. Disparando recálculo de stock...")
        try:
            Stock.recalcular_stock_completo(
                self.empresa_id,
                self.almacen_origen_id,
                self.producto_id
            )
            Stock.recalcular_stock_completo(
                self.empresa_id,
                self.almacen_destino_id,
                self.producto_id
            )
            logger.info(f"Recálculo completado para {self.id}.")
        except Exception as e:
            logger.error(f"Error en recálculo de stock POST-COMMIT para {self.id}: {e}", exc_info=True)

    def recibir_mercaderia(self, cantidad_recibida, fecha_recepcion, notas='', auto_recepcion=False,
                           _skip_recalc_signal=False):
        if self.estado != 'EN_TRANSITO':
            return False

        # 1. Actualizar estado de la Transferencia
        recibida = cantidad_recibida or 0
        diferencia = recibida - self.cantidad_enviada
        self.cantidad_recibida = recibida
        self.cantidad_diferencia = diferencia

        # Fecha de recepción (o ahora)
        fecha_final = fecha_recepcion or timezone.now()
        self.fecha_recepcion = fecha_final
        self.notas_recepcion = notas

        # Lógica de Estado
        if recibida <= 0:
            self.estado = 'PERDIDO'
        elif diferencia > 0:
            self.estado = 'RECIBIDO_SOBRANTE'
        elif diferencia < 0:
            self.estado = 'RECIBIDO_PARCIAL'
        else:
            self.estado = 'RECIBIDO'

        self.save()

        # 2. CREAR EL MOVIMIENTO (NI) USANDO DATA LEGACY
        if self.estado in ['RECIBIDO', 'RECIBIDO_PARCIAL', 'RECIBIDO_SOBRANTE']:
            from .models import MovimientoAlmacen, LegacyMovAlmCab, LegacyMovAlmDet

            # A. Identificar IDs
            # Si el sync ya vinculó la NI, usamos ese ID. Si no, generamos uno temporal.
            pk_det = self.id_erp_ingreso_det or f"WEB-TR-{self.id}-IN"
            pk_cab = self.id_erp_ingreso_cab or f"WEB-TR-{self.id}"

            # B. Intentar buscar la DATA RICA en Legacy
            datos_movimiento = {}
            legacy_found = False

            if self.id_erp_ingreso_det:
                try:
                    # Desglosamos el ID: AL-NI-000456-1 -> Emp, Alm, TD, Num, Item
                    # Asumiendo que id_erp_ingreso_det guarda la PK exacta de Legacy
                    parts = self.id_erp_ingreso_det.split('-')
                    # parts[0]=AL, parts[1]=NI, parts[2]=NUM, parts[3]=ITEM

                    if len(parts) >= 4:
                        item_erp = int(parts[3])

                        # Buscamos el detalle específico
                        det_legacy = LegacyMovAlmDet.objects.get(
                            empresa=self.empresa,
                            dealma=parts[0],  # Almacén
                            detd=parts[1],  # TD
                            denumdoc=parts[2],  # Número
                            deitem=item_erp
                        )

                        # Buscamos la cabecera para fechas y glosas
                        cab_legacy = LegacyMovAlmCab.objects.get(
                            empresa=self.empresa,
                            caalma=parts[0],
                            catd=parts[1],
                            canumdoc=parts[2]
                        )

                        fecha_precisa = cab_legacy.cafecdoc

                        if cab_legacy.cafecdoc and cab_legacy.cahora:
                            try:
                                # Limpiamos y parseamos la hora
                                hora_str = str(cab_legacy.cahora).strip()
                                hora_obj = datetime.datetime.strptime(hora_str, "%H:%M:%S").time()

                                # Combinamos Fecha + Hora
                                dt_combinado = datetime.datetime.combine(cab_legacy.cafecdoc.date(), hora_obj)

                                # Asignamos zona horaria (UTC o Local)
                                if settings.USE_TZ:
                                    fecha_precisa = timezone.make_aware(dt_combinado, timezone.get_current_timezone())
                                else:
                                    fecha_precisa = dt_combinado
                            except ValueError:
                                pass  # Si falla, mantenemos la fecha original (00:00:00)
                        # -------------------------------------

                        # ¡ÉXITO! TENEMOS LOS DATOS EXACTOS DEL ERP
                        legacy_found = True
                        datos_movimiento = {
                            'tipo_documento_erp': cab_legacy.catd.strip(),
                            'numero_documento_erp': det_legacy.denumdoc.strip(),
                            'item_erp': det_legacy.deitem,
                            'fecha_documento': fecha_precisa,
                            'fecha_movimiento': cab_legacy.cafecact or cab_legacy.cafecdoc,
                            'cantidad': recibida,  # Usamos lo recibido real, no lo del legacy si difiere
                            'costo_unitario': det_legacy.depreuni or 0,
                            'valor_total': det_legacy.devaltot or 0,
                            'estado_erp': cab_legacy.casitgui,
                            'glosa_cabecera': (cab_legacy.caglosa or '')[:500],
                            'glosa_detalle': det_legacy.deglosa,
                            'almacen_ref': cab_legacy.carfalma or '',
                            'referencia_documento': cab_legacy.carfndoc,
                            'codigo_movimiento': (cab_legacy.cacodmov or '').strip(),
                            'motivo_tras': (cab_legacy.motivo_gs or '').strip(),
                            'direccion_envio_erp': (cab_legacy.cadirenv or '').strip(),
                            'lote': det_legacy.delote or '',
                            'numero_orden_compra': cab_legacy.canumord or '',
                            'unidad_medida_erp': det_legacy.deunidad or '',
                        }
                except Exception as e:
                    logger.warning(
                        f"Recepción Manual TR-{self.id}: No se encontró data Legacy ({e}). Usando datos básicos.")

            # C. Si no encontramos Legacy (Empate o Sync pendiente), usamos datos básicos
            if not legacy_found:
                datos_movimiento = {
                    'tipo_documento_erp': 'NI',  # Default
                    'numero_documento_erp': f"TR-{self.id}",
                    'item_erp': 1,
                    'fecha_documento': fecha_final,
                    'fecha_movimiento': fecha_final,
                    'cantidad': recibida,
                    'costo_unitario': 0,
                    'valor_total': 0,
                    'estado_erp': 'F',
                    'glosa_cabecera': f"Transferencia recibida de {self.almacen_origen.descripcion}",
                    'referencia_documento': self.id_erp_salida_cab,
                    'codigo_movimiento': 'TD',
                }

            # D. Crear/Actualizar el Movimiento
            MovimientoAlmacen.objects.update_or_create(
                empresa=self.empresa,
                id_erp_det=pk_det,
                defaults={
                    'id_erp_cab': pk_cab,
                    'almacen': self.almacen_destino,
                    'producto': self.producto,
                    'es_ingreso': True,
                    'state': True,
                    **datos_movimiento  # Desempaquetamos los datos (Legacy o Básicos)
                }
            )

        # 3. Recálculo de Stock
        if not _skip_recalc_signal:
            logger.info(f"Transferencia {self.id} recibida. Recalculando stock.")
            transaction.on_commit(self._disparar_recalculo_stock)
        else:
            logger.info(f"Transferencia {self.id} recibida (re-cálculo omitido).")

        return True

    def revertir_recepcion(self):
        """
        Revierte una transferencia a 'EN_TRANSITO' y ELIMINA el movimiento de ingreso generado.
        """
        if self.estado == 'EN_TRANSITO':
            logger.warning(f"Intento de revertir transferencia {self.id} que ya está EN TRANSITO.")
            return False

        # --- 1. ¡NUEVO! ELIMINAR EL MOVIMIENTO DE ALMACÉN ---
        # Importamos aquí para evitar referencia circular
        from .models import MovimientoAlmacen

        # Buscamos el movimiento usando la misma clave (ID) que usamos para crearlo.
        # Nota: Usamos 'id_erp_ingreso_det' o el ID generado por la web.
        id_bussines_key = self.id_erp_ingreso_det or f"WEB-TR-{self.id}-IN"

        deleted_count, _ = MovimientoAlmacen.objects.filter(
            empresa=self.empresa,
            id_erp_det=id_bussines_key
        ).delete()

        logger.info(f"Reversión TR-{self.id}: Se eliminaron {deleted_count} registros de MovimientoAlmacen.")

        # --- 2. Restablecer los campos de la Transferencia ---
        logger.info(f"Revirtiendo estado para {self.id}. Anterior: {self.estado}")
        self.estado = 'EN_TRANSITO'
        self.cantidad_recibida = None
        self.cantidad_diferencia = None
        self.fecha_recepcion = None
        self.notas_recepcion = f"Recepción revertida por usuario el {timezone.now()}."

        # --- 3. Guardar cambios en la Transferencia ---
        self.save()

        # --- 4. Recalcular Stock ---
        # Ahora que borramos el MovimientoAlmacen, al recalcular, el stock bajará.
        # IMPORTANTE: Sin paréntesis en la función, como corregimos antes.
        transaction.on_commit(self._disparar_recalculo_stock)

        logger.info(f"Transferencia {self.id} revertida exitosamente.")
        return True


class GastoDocumentoAlmacen(base.models.BaseModel):  # Hereda de BaseModel
    """
    Registra gastos asociados a un documento de movimiento de almacén
    completo (ej. estibaje para una Guía de Salida).
    """
    # --- Vinculación ---
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='gastos_documentos')
    # Clave del documento de cabecera en el ERP al que se asocia este gasto
    id_erp_cab = models.CharField(
        max_length=50,
        db_index=True,  # Importante para búsquedas rápidas
        help_text="PK de MOVALMCAB (ej: AD-GS-0000001)"
    )
    # Opcional: Podrías linkearlo a MovimientoAlmacen si un gasto fuera por línea,
    # pero para gastos por documento, id_erp_cab es suficiente.

    # --- Datos del Gasto ---
    TIPO_GASTO_CHOICES = [
        ('EST', 'Estibaje'),
        ('TRN', 'Transporte'),
        ('SEG', 'Seguro'),
        ('OTR', 'Otros'),
    ]
    tipo_gasto = models.CharField(
        max_length=3,
        choices=TIPO_GASTO_CHOICES,
        default='OTR'
    )
    descripcion = models.TextField(blank=True, null=True, help_text="Detalles adicionales del gasto")
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_gasto = models.DateField(default=timezone.now)  # O DateTimeField si necesitas la hora

    class Meta:
        verbose_name = "Gasto de Documento de Almacén"
        verbose_name_plural = "Gastos de Documentos de Almacén"
        # Permitir múltiples gastos por documento (ej. estibaje y transporte)
        # Por eso no hacemos unique_together con id_erp_cab
        indexes = [
            models.Index(fields=['empresa', 'id_erp_cab']),  # Para buscar gastos por documento
        ]

    def __str__(self):
        return f"{self.get_tipo_gasto_display()} - {self.monto} ({self.id_erp_cab})"


class ControlSyncMovAlmacen(models.Model):
    """
    Registra la última fecha/hora de sincronización exitosa
    para movimientos de almacén (MOVALMCAB/DET) de una Empresa específica.
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE
    )
    # Ya no necesitamos 'tabla_erp' si este modelo es *solo* para MovAlmacen
    ultima_fecha = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp del último registro ERP procesado (ej: CAFECACT)"
    )
    last_full_sync_run = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Cuándo se ejecutó la última comparación completa de claves (para anulaciones)"
    )

    class Meta:
        # Hacemos que la empresa sea la clave primaria si solo hay una entrada por empresa
        constraints = [
            models.UniqueConstraint(fields=['empresa'], name='unique_empresa_sync_movalmacen')
        ]
        verbose_name = "Control Sincronización Mov. Almacén"
        verbose_name_plural = "Controles Sincronización Mov. Almacén"

    def __str__(self):
        fecha_str = self.ultima_fecha.strftime('%Y-%m-%d %H:%M:%S') if self.ultima_fecha else 'Nunca'
        return f"Sync MovAlm {self.empresa.nombre_empresa}: {fecha_str}"






