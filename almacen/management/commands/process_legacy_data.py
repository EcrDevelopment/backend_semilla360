# almacen/management/commands/process_legacy_data.py

import logging
import re  # <--- IMPORTANTE: Necesario para la Regex
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
import datetime

# Modelos de BD Local (MySQL)
from importaciones.models import Empresa, Producto
from almacen.models import (
    LegacyMovAlmCab, LegacyMovAlmDet,
    MovimientoAlmacen, Transferencia, Stock, Almacen, MovimientoAlmacenNota
)
from semilla360 import settings

logger = logging.getLogger(__name__)

# --- PARÁMETROS DE LÓGICA DE NEGOCIO ---
DIAS_PARA_AUTO_RECEPCION = 4
TIPOS_DOC_RELEVANTES = ['NI', 'GS', 'TR', 'TK', 'NS', 'BV', 'NC', 'FT']


class Command(BaseCommand):
    help = 'FASE 2: Procesa datos Legacy. Usa CATIPMOV para dirección. Maneja actualizaciones y anulaciones.'

    def add_arguments(self, parser):
        parser.add_argument('empresa_alias', type=str)
        parser.add_argument('--reset-clean-data', action='store_true')
        parser.add_argument('--days', type=int, default=30)

    def handle(self, *args, **options):
        empresa_alias = options['empresa_alias']
        reset_data = options['reset_clean_data']
        days_window = options['days']
        ahora = timezone.now()

        try:
            empresa = Empresa.objects.get(nombre_empresa=empresa_alias)
        except Empresa.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Empresa '{empresa_alias}' no encontrada."))
            return

        self.stdout.write(self.style.SUCCESS(f"=== FASE 2 - {empresa_alias} ==="))

        # --- PRE-CARGA DE MAPA DE SEDES ---
        # Mapeamos las series de documentos (001, 002, 003) a los IDs de almacenes físicos
        mapa_sedes_cache = {}
        try:
            # 001 -> Lima (AL), 002 -> Arequipa (AA), 003 -> Desaguadero (AD)
            mapa_sedes_cache['001'] = Almacen.objects.get(empresa=empresa, codigo='AL').id
            mapa_sedes_cache['002'] = Almacen.objects.get(empresa=empresa, codigo='AA').id
            mapa_sedes_cache['003'] = Almacen.objects.get(empresa=empresa, codigo='AD').id
            self.stdout.write("✅ Mapa de sedes cargado correctamente (001=AL, 002=AA, 003=AD).")
        except Almacen.DoesNotExist as e:
            self.stdout.write(self.style.WARNING(f"⚠️ Alerta: Faltan almacenes para mapeo de sedes: {e}"))
        # ----------------------------------

        fecha_corte = None
        if reset_data:
            self.stdout.write(self.style.WARNING("Reseteando tablas limpias..."))
            with transaction.atomic():
                Transferencia.objects.filter(empresa=empresa).delete()
                MovimientoAlmacen.objects.filter(empresa=empresa).delete()
                Stock.objects.filter(empresa=empresa).delete()
            self.stdout.write(self.style.SUCCESS("Tablas limpias borradas."))
        else:
            fecha_corte = ahora - datetime.timedelta(days=days_window)
            self.stdout.write(f"Procesando desde: {fecha_corte.strftime('%Y-%m-%d')}")

        # Query Base
        query = Q(empresa=empresa, catd__in=TIPOS_DOC_RELEVANTES)
        if fecha_corte:
            query &= Q(cafecdoc__gte=fecha_corte)

        cabeceras = LegacyMovAlmCab.objects.filter(query).order_by('cafecdoc')
        count = cabeceras.count()
        self.stdout.write(f"Procesando {count} cabeceras legacy...")

        productos_afectados = set()

        with transaction.atomic():
            for i, cab in enumerate(cabeceras.iterator()):
                if i % 2000 == 0 and i > 0: self.stdout.write(f"  {i}/{count}...")

                # --- MANEJO DE ANULADOS (V -> A) ---
                if cab.casitgui == 'A':
                    pk_cab_anulada = f"{cab.caalma.strip()}-{cab.catd.strip()}-{cab.canumdoc.strip()}"
                    deleted, _ = MovimientoAlmacen.objects.filter(empresa=empresa, id_erp_cab=pk_cab_anulada).delete()
                    if deleted > 0:
                        pass  # Aquí se podría disparar recálculo específico si se desea
                    continue

                # --- INICIO PROCESAMIENTO NORMAL ---
                try:
                    alm_local = Almacen.objects.get(empresa=empresa, codigo=cab.caalma.strip())
                except Almacen.DoesNotExist:
                    continue

                detalles = LegacyMovAlmDet.objects.filter(
                    empresa=empresa, dealma=cab.caalma, detd=cab.catd, denumdoc=cab.canumdoc
                ).order_by('deitem')

                if not detalles.exists(): continue

                for det in detalles:
                    # Filtro Texto
                    cod_prod_raw = det.decodigo.strip() if det.decodigo else None
                    if not cod_prod_raw or cod_prod_raw.upper() == 'TEXTO':
                        crear_nota_almacen(empresa, pk_cab, pk_det, det)
                        continue

                    try:
                        prod_local = Producto.objects.get(empresa=empresa, codigo_producto=cod_prod_raw)
                    except Producto.DoesNotExist:
                        continue

                    productos_afectados.add((alm_local.id, prod_local.id))

                    pk_cab = f"{cab.caalma.strip()}-{cab.catd.strip()}-{cab.canumdoc.strip()}"
                    pk_det = f"{pk_cab}-{det.deitem}"

                    # === SEMÁFORO ===
                    # Se pasa 'mapa_sedes_cache' a todas las funciones
                    if cab.cacodmov == 'TD':
                        if cab.catipmov == 'I':
                            # NI-TD (Entrada)
                            process_ingreso_traslado(empresa, cab, det, pk_cab, pk_det, alm_local, prod_local,
                                                     productos_afectados, ahora, mapa_sedes_cache)
                        else:
                            # GS-TD (Salida)
                            process_salida_traslado(empresa, cab, det, pk_cab, pk_det, alm_local, prod_local, ahora,
                                                    mapa_sedes_cache)
                    else:
                        # Movimiento Normal (Compras/Ventas)
                        process_movimiento_normal(empresa, cab, det, pk_cab, pk_det, alm_local, prod_local,
                                                  mapa_sedes_cache)

        # Recálculo Final
        self.stdout.write(self.style.WARNING("Recalculando stock..."))
        with transaction.atomic():
            if reset_data: Stock.objects.filter(empresa=empresa).delete()

            for idx, (aid, pid) in enumerate(productos_afectados):
                if idx % 1000 == 0: self.stdout.write(f"  Recalc {idx}...")
                try:
                    Stock.recalcular_stock_completo(empresa.id, aid, pid)
                except Exception:
                    pass

        self.stdout.write(self.style.SUCCESS("¡Proceso Finalizado!"))


# --- FUNCIONES AUXILIARES ---

# ==========================================
# FUNCIONES AUXILIARES FASE 2 (COMMAND OPTIMIZADO)
# ==========================================

def process_movimiento_normal(empresa, cab, det, pk_cab, pk_det, alm, prod, mapa_sedes_cache=None):
    """
    Procesa movimientos normales.
    Lógica IN/OUT basada estrictamente en CATIPMOV ('I'/'S').
    """
    doc_tipo = cab.catd.strip()
    cod_mov = (cab.cacodmov or '').strip()
    sit_gui = (cab.casitgui or '').strip()

    # Filtro SP: Ignorar GS-GF-F (Guías facturadas)
    if doc_tipo == 'GS' and cod_mov == 'GF' and sit_gui == 'F': return

    # Filtro SP: Ignorar NS-AJ (Ajustes) - (Comentado según tu código anterior)
    '''
    if doc_tipo == 'NS' and cod_mov == 'AJ':
        if (det.decantid or 0) <= 0:
            return  # Ignorar ajustes sin cantidad
    '''

    # --- Lógica IN/OUT ---
    es_ingreso = (cab.catipmov == 'I')

    crear_movimiento_en_db(empresa, cab, det, pk_cab, pk_det, alm, prod, es_ingreso, mapa_sedes_cache)


def process_salida_traslado(empresa, cab, det, pk_cab, pk_det, alm, prod, ahora, mapa_sedes_cache=None):
    """GS-TD (Salida): Crea Transferencia y SIEMPRE crea MovimientoAlmacen (Salida)."""

    try:
        alm_destino = Almacen.objects.get(empresa=empresa, codigo=cab.carfalma.strip())
    except Almacen.DoesNotExist:
        return

    # --- LÓGICA FECHA PRECISA ---
    fecha_precisa = cab.cafecdoc
    if cab.cafecdoc and cab.cahora:
        try:
            hora_str = str(cab.cahora).strip()
            hora_obj = datetime.datetime.strptime(hora_str, "%H:%M:%S").time()
            dt_naive = datetime.datetime.combine(cab.cafecdoc.date(), hora_obj)
            if settings.USE_TZ:
                fecha_precisa = timezone.make_aware(dt_naive)
            else:
                fecha_precisa = dt_naive
        except ValueError: pass
    # ---------------------------

    try:
        transf = Transferencia.objects.get(empresa=empresa, id_erp_salida_det=pk_det, producto=prod)
        transf.id_erp_salida_cab = pk_cab
        transf.almacen_origen = alm
        transf.cantidad_enviada = det.decantid or 0
        transf.fecha_envio = fecha_precisa  # <--- Usamos fecha con hora

        # Validación de fecha para no sobrescribir estado de recientes
        if transf.id_erp_ingreso_det:
            limite = ahora - datetime.timedelta(days=DIAS_PARA_AUTO_RECEPCION)
            # Comparamos fecha precisa vs limite
            if fecha_precisa < limite:
                transf.estado = 'RECIBIDO'
                transf.cantidad_recibida = det.decantid
                # Guardamos la fecha de recepción también con hora exacta
                transf.fecha_recepcion = transf.fecha_recepcion or fecha_precisa

        transf.save()

    except Transferencia.DoesNotExist:
        Transferencia.objects.create(
            empresa=empresa, id_erp_salida_det=pk_det, id_erp_salida_cab=pk_cab,
            almacen_origen=alm, almacen_destino=alm_destino, producto=prod,
            cantidad_enviada=det.decantid or 0,
            fecha_envio=fecha_precisa,  # <--- Fecha precisa al crear
            estado='EN_TRANSITO'
        )

    # Salida física inmediata (es_ingreso=False)
    crear_movimiento_en_db(empresa, cab, det, pk_cab, pk_det, alm, prod, es_ingreso=False,
                           mapa_sedes_cache=mapa_sedes_cache)


def process_ingreso_traslado(empresa, cab, det, pk_cab, pk_det, alm, prod, productos_afectados, ahora,
                             mapa_sedes_cache=None):
    """NI-TD (Entrada): Crea Transferencia. Solo crea Movimiento si Auto-Recepciona."""

    id_gs = f"{cab.carfalma.strip()}-{cab.carftdoc.strip()}-{cab.carfndoc.strip()}-{det.deitem}"

    try:
        alm_origen = Almacen.objects.get(empresa=empresa, codigo=cab.carfalma.strip())
    except Almacen.DoesNotExist:
        try:
            alm_origen = Almacen.objects.get(empresa=empresa, codigo='NA')
        except Almacen.DoesNotExist:
            alm_origen = alm

    # --- LÓGICA FECHA PRECISA ---
    fecha_precisa = cab.cafecdoc
    if cab.cafecdoc and cab.cahora:
        try:
            hora_str = str(cab.cahora).strip()
            hora_obj = datetime.datetime.strptime(hora_str, "%H:%M:%S").time()
            dt_naive = datetime.datetime.combine(cab.cafecdoc.date(), hora_obj)
            if settings.USE_TZ:
                fecha_precisa = timezone.make_aware(dt_naive)
            else:
                fecha_precisa = dt_naive
        except ValueError: pass
    # ---------------------------

    transf, created = Transferencia.objects.get_or_create(
        empresa=empresa, id_erp_salida_det=id_gs, producto=prod,
        defaults={
            'almacen_origen': alm_origen,
            'almacen_destino': alm,
            'cantidad_enviada': det.decantid or 0,
            'fecha_envio': fecha_precisa, # Fecha precisa
            'estado': 'EN_TRANSITO'
        }
    )

    transf.id_erp_ingreso_det = pk_det
    transf.id_erp_ingreso_cab = pk_cab
    transf.almacen_destino = alm

    debe_crear_movimiento = False
    limite = ahora - datetime.timedelta(days=DIAS_PARA_AUTO_RECEPCION)

    if fecha_precisa < limite:
        transf.estado = 'RECIBIDO'
        transf.cantidad_recibida = det.decantid
        transf.fecha_recepcion = fecha_precisa # Fecha precisa
        debe_crear_movimiento = True

    transf.save()
    productos_afectados.add((alm.id, prod.id))

    if debe_crear_movimiento:
        crear_movimiento_en_db(empresa, cab, det, pk_cab, pk_det, alm, prod, es_ingreso=True,
                               mapa_sedes_cache=mapa_sedes_cache)


def crear_movimiento_en_db(empresa, cab, det, pk_cab, pk_det, alm, prod, es_ingreso, mapa_sedes_cache=None):
    item_val = det.deitem
    if item_val is None:
        try:
            item_val = int(pk_det.split('-')[-1])
        except:
            item_val = 0

    # 1. Lógica Sede Facturación
    sede_facturacion_id = None
    if cab.catd.strip() == 'GS' and (cab.cacodmov or '').strip() == 'GV' and cab.casitgui == 'F':
        referencia = (cab.carfndoc or '').strip()
        if referencia and mapa_sedes_cache:
            match = re.search(r"^[A-Z]+([0-9]{3})", referencia)
            if match: sede_facturacion_id = mapa_sedes_cache.get(match.group(1))

    # 2. Lógica Fecha + Hora
    fecha_precisa = cab.cafecdoc
    if cab.cafecdoc and cab.cahora:
        try:
            hora_str = str(cab.cahora).strip()
            hora_obj = datetime.datetime.strptime(hora_str, "%H:%M:%S").time()
            dt_naive = datetime.datetime.combine(cab.cafecdoc.date(), hora_obj)
            if settings.USE_TZ:
                fecha_precisa = timezone.make_aware(dt_naive)
            else:
                fecha_precisa = dt_naive
        except ValueError: pass

    MovimientoAlmacen.objects.update_or_create(
        empresa=empresa, id_erp_det=pk_det,
        defaults={
            'id_erp_cab': pk_cab, 'almacen': alm, 'producto': prod,
            'es_ingreso': es_ingreso, 'almacen_ref': cab.carfalma,
            'tipo_documento_erp': cab.catd.strip(),
            'numero_documento_erp': det.denumdoc.strip(),
            'item_erp': item_val,
            'fecha_documento': fecha_precisa, # <--- Fecha CON HORA
            'fecha_movimiento': cab.cafecact or fecha_precisa,
            'cantidad': det.decantid or 0,
            'costo_unitario': det.depreuni or 0, 'valor_total': det.devaltot or 0,
            'lote': det.delote or '',
            'numero_orden_compra': cab.canumord or '',
            'unidad_medida_erp': det.deunidad or '',
            'estado_erp': cab.casitgui,
            'glosa_cabecera': (cab.caglosa or '')[:500],
            'referencia_documento': cab.carfndoc,
            'sede_facturacion_id': sede_facturacion_id,
            'codigo_movimiento': (cab.cacodmov or '').strip(),
            'cliente_erp_id': (cab.cacodcli or '').strip(),
            'cliente_erp_nombre': (cab.canomcli or '').strip(),
            'nombre_proveedor': (cab.canompro or '').strip(),
            'direccion_envio_erp': (cab.cadirenv or '').strip(),
            'motivo_tras': (cab.motivo_gs or '').strip(),
            'id_importacion': (cab.canroimp),
            'importacion': (cab.caimportacion),
            'proveedor_erp_id': cab.cacodpro,
            'state': True
        }
    )



def crear_nota_almacen(empresa, pk_cab, pk_det, det):
    """
    Crea un registro en MovimientoAlmacenNota si el detalle es 'TEXTO'.
    """
    try:
        MovimientoAlmacenNota.objects.update_or_create(
            empresa=empresa,
            id_erp_det=pk_det,
            defaults={
                'id_erp_cab': pk_cab,
                'item_erp': det.deitem,
                'texto_descripcion': det.dedescri, # Descripción principal
                'texto_detalle': det.detexto,      # Detalle extendido
                # Puedes agregar 'created_by' o lo que necesites de BaseModel
            }
        )
    except Exception as e:
        # Logueamos pero no detenemos el proceso por una nota
        logger.error(f"Error creando nota {pk_det}: {e}")

'''

def crear_movimiento_en_db(empresa, cab, det, pk_cab, pk_det, alm, prod, es_ingreso, mapa_sedes_cache=None):
    """Helper blindado contra errores de integridad. Actualiza si ya existe."""

    item_val = det.deitem
    if item_val is None:
        try:
            item_val = int(pk_det.split('-')[-1])
        except:
            item_val = 0

    # --- LÓGICA SEDE FACTURACIÓN (NUEVO) ---
    sede_facturacion_id = None
    # Solo procesamos si es GS (Guía Salida) - GV (Venta) - Estado F (Facturado)
    if cab.catd.strip() == 'GS' and (cab.cacodmov or '').strip() == 'GV' and cab.casitgui == 'F':
        referencia = (cab.carfndoc or '').strip()  # Ej: "F0010006410"

        if referencia and mapa_sedes_cache:
            # Busca letras al inicio y captura los siguientes 3 dígitos
            match = re.search(r"^[A-Z]+([0-9]{3})", referencia)
            if match:
                codigo_serie = match.group(1)  # Ej: "001"
                sede_facturacion_id = mapa_sedes_cache.get(codigo_serie)
    # ---------------------------------------

    fecha_precisa = cab.cafecdoc

    if cab.cafecdoc and cab.cahora:
        try:
            # Limpiamos la hora por si viene con espacios
            hora_str = str(cab.cahora).strip()

            # Parseamos la hora (HH:MM:SS)
            hora_obj = datetime.datetime.strptime(hora_str, "%H:%M:%S").time()

            # Combinamos Fecha + Hora
            dt_combinado = datetime.datetime.combine(cab.cafecdoc.date(), hora_obj)

            # Le ponemos la zona horaria correcta (UTC o la de tu settings)
            if settings.USE_TZ:
                fecha_precisa = timezone.make_aware(dt_combinado, timezone.get_current_timezone())
            else:
                fecha_precisa = dt_combinado

        except ValueError:
            # Si la hora falla (formato incorrecto), nos quedamos con la fecha original
            pass

    # update_or_create manejará las actualizaciones de campos (V->F) automáticamente
    MovimientoAlmacen.objects.update_or_create(
        empresa=empresa, id_erp_det=pk_det,
        defaults={
            'id_erp_cab': pk_cab, 'almacen': alm, 'producto': prod,
            'es_ingreso': es_ingreso, 'almacen_ref': cab.carfalma,
            'tipo_documento_erp': cab.catd.strip(),
            'numero_documento_erp': det.denumdoc.strip(),
            'item_erp': item_val,
            'fecha_documento': fecha_precisa,
            'fecha_movimiento': cab.cafecact or cab.cafecdoc,
            'cantidad': det.decantid or 0,
            'costo_unitario': det.depreuni or 0, 'valor_total': det.devaltot or 0,
            'lote': det.delote or '',
            'numero_orden_compra': cab.canumord or '',
            'unidad_medida_erp': det.deunidad or '',
            'estado_erp': cab.casitgui,
            'glosa_cabecera': (cab.caglosa or '')[:500],
            'referencia_documento': cab.carfndoc,
            'sede_facturacion_id': sede_facturacion_id,
            'codigo_movimiento': (cab.cacodmov or '').strip(),
            'cliente_erp_id': (cab.cacodcli or '').strip(),
            'cliente_erp_nombre': (cab.canomcli or '').strip(),
            'nombre_proveedor': (cab.canompro or '').strip(),
            'direccion_envio_erp': (cab.cadirenv or '').strip(),
            'motivo_tras': (cab.motivo_gs or '').strip(),
            'state': True
        }
    )
'''