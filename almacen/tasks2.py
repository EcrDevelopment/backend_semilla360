import logging
import re  # <--- Importante para la Regex
import datetime
import traceback
from django_rq import job
from django.utils import timezone
from django.db import connections, transaction
from django.db.models import Q
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Modelos
from .models import (
    MovAlmCab, MovAlmDet,
    LegacyMovAlmCab, LegacyMovAlmDet, ControlSyncMovAlmacen,
    MovimientoAlmacen, Transferencia, Stock, Almacen  # <-- Modelos Fase 2
)
from importaciones.models import Empresa, Producto

logger = logging.getLogger(__name__)

TIPOS_DOC_RELEVANTES = ['NI', 'GS', 'TR', 'TK', 'NS', 'BV', 'NC', 'FT']
DIAS_PARA_AUTO_RECEPCION = 4  # Config Fase 2


# --- FUNCIONES DE NOTIFICACIÓN ---
def notificar_grupo_empresa(empresa_id, status, message, result=None):
    if not empresa_id: return
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            grupo = f"sync_movimientos_empresa_{empresa_id}"
            evento = {'type': 'sync.update', 'status': status, 'message': message}
            if result: evento['result'] = result
            async_to_sync(channel_layer.group_send)(grupo, evento)
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")


@job('default', timeout=7200)
def sincronizar_empresa_erp_task(empresa_alias, start_year=2000, reconciliation_days=30, user_id=None):
    """
    MASTER TASK: Ejecuta Fase 1 (Extracción) y Fase 2 (Procesamiento) secuencialmente.
    """
    ahora = timezone.now()
    db_alias = empresa_alias

    logger.info(f'--- INICIO MASTER SYNC para {db_alias} ---')

    try:
        # 1. Validar empresa
        if db_alias not in connections: raise Exception(f"Alias '{db_alias}' no configurado.")
        try:
            empresa = Empresa.objects.get(nombre_empresa=db_alias)
        except Empresa.DoesNotExist:
            raise Exception(f"Empresa '{db_alias}' no existe.")

        notificar_grupo_empresa(empresa.id, 'started',
                                f'Iniciando Sincronización Completa para {empresa.razon_social}...')

        # ==========================================
        # FASE 1: EXTRACCIÓN (ERP -> Legacy)
        # ==========================================
        notificar_grupo_empresa(empresa.id, 'running_f1', 'Fase 1: Extrayendo datos del ERP...')

        # ... (Aquí va la lógica de Control Sync, Copia Incremental y Reconciliación) ...
        # ... (Para resumir, uso la lógica que ya teníamos validada) ...

        # A) Control Sync
        fecha_inicio_sync = datetime.datetime(start_year, 1, 1, tzinfo=datetime.timezone.utc)
        control_sync, created = ControlSyncMovAlmacen.objects.get_or_create(
            empresa=empresa, defaults={'ultima_fecha': fecha_inicio_sync}
        )
        ultima_sync_fecha = control_sync.ultima_fecha if not created else fecha_inicio_sync
        if settings.USE_TZ and timezone.is_naive(ultima_sync_fecha):
            ultima_sync_fecha = timezone.make_aware(ultima_sync_fecha, datetime.timezone.utc)

        if ultima_sync_fecha:
            ultima_sync_fecha = ultima_sync_fecha.replace(hour=0, minute=0, second=0)

        # B) Copia Incremental
        cabeceras_nuevas = MovAlmCab.objects.using(db_alias).filter(
            Q(cafecdoc__gte=ultima_sync_fecha),
            catd__in=TIPOS_DOC_RELEVANTES
        ).order_by('cafecdoc')

        if cabeceras_nuevas.exists():
            ultima_fecha_ok = None
            with transaction.atomic(using='default'):
                for cab_erp in cabeceras_nuevas.iterator():
                    # Copiar Cabecera
                    cab_defaults = {
                        'cafecdoc': cab_erp.cafecdoc, 'catipmov': cab_erp.catipmov,
                        'cacodmov': cab_erp.cacodmov, 'casitua': cab_erp.casitua,
                        'carftdoc': cab_erp.carftdoc, 'carfndoc': cab_erp.carfndoc,
                        'casoli': cab_erp.casoli, 'cafecdev': cab_erp.cafecdev,
                        'cacodpro': cab_erp.cacodpro, 'cacencos': cab_erp.cacencos,
                        'carfalma': cab_erp.carfalma, 'caglosa': cab_erp.caglosa,
                        'cafecact': cab_erp.cafecact, 'cahora': cab_erp.cahora,
                        'causuari': cab_erp.causuari, 'cacodcli': cab_erp.cacodcli,
                        'canomcli': cab_erp.canomcli, 'casitgui': cab_erp.casitgui,
                        'canompro': cab_erp.canompro, 'canomtra': cab_erp.canomtra,
                        'cacodtran': cab_erp.cacodtran, 'caimportacion': cab_erp.caimportacion,
                        'canroimp': cab_erp.canroimp, 'motivo_gs': cab_erp.motivo_gs,
                        'canumord': cab_erp.canumord, 'cadirenv': cab_erp.cadirenv,
                    }
                    LegacyMovAlmCab.objects.update_or_create(
                        empresa=empresa, caalma=cab_erp.caalma, catd=cab_erp.catd,
                        canumdoc=cab_erp.canumdoc, defaults=cab_defaults
                    )
                    # Copiar Detalles
                    detalles_erp = MovAlmDet.objects.using(db_alias).filter(
                        dealma=cab_erp.caalma, detd=cab_erp.catd, denumdoc=cab_erp.canumdoc
                    ).order_by('deitem')
                    for det_erp in detalles_erp:
                        det_defaults = {
                            'decodigo': det_erp.decodigo, 'decantid': det_erp.decantid,
                            'depreuni': det_erp.depreuni, 'deserie': det_erp.deserie,
                            'defecdoc': det_erp.defecdoc, 'deglosa': det_erp.deglosa,
                            'delote': det_erp.delote, 'deunidad': det_erp.deunidad,
                            'devaltot': det_erp.devaltot, 'dedescri': det_erp.dedescri,
                            'detexto': det_erp.detexto,
                        }
                        LegacyMovAlmDet.objects.update_or_create(
                            empresa=empresa, dealma=det_erp.dealma, detd=det_erp.detd,
                            denumdoc=det_erp.denumdoc, deitem=det_erp.deitem, defaults=det_defaults
                        )
                    if cab_erp.cafecdoc: ultima_fecha_ok = cab_erp.cafecdoc

            if ultima_fecha_ok:
                control_sync.ultima_fecha = ultima_fecha_ok
                control_sync.save(update_fields=['ultima_fecha'])

        # C) Reconciliación Fase 1
        reconciliar_datos_recientes_f1(empresa, db_alias, ahora, reconciliation_days)
        control_sync.last_full_sync_run = ahora
        control_sync.save(update_fields=['last_full_sync_run'])

        # ==========================================
        # FASE 2: PROCESAMIENTO (Legacy -> Final)
        # ==========================================
        notificar_grupo_empresa(empresa.id, 'running_f2', 'Fase 2: Procesando reglas de negocio...')

        # Ejecutamos la lógica que antes estaba en el comando
        procesar_legacy_data_logic(empresa, ahora, reconciliation_days)

    except Exception as e_main:
        logger.error(f"Error FATAL en Sync: {e_main}", exc_info=True)
        notificar_grupo_empresa(empresa.id, 'failed', str(e_main))
        return f"Error: {e_main}"

    msg = f"Sincronización completa (Fase 1 y 2) finalizada."
    notificar_grupo_empresa(empresa.id, 'finished', "Proceso Exitoso.", result=msg)
    return msg


# --- LÓGICA FASE 1 AUXILIAR ---
def reconciliar_datos_recientes_f1(empresa, db_alias, ahora, dias_atras):
    """
    Lógica original de reconciliación de la Fase 1.
    """
    fecha_inicio = ahora - datetime.timedelta(days=dias_atras)
    try:
        cabeceras_erp = MovAlmCab.objects.using(db_alias).filter(
            catd__in=TIPOS_DOC_RELEVANTES,
            cafecdoc__gt=fecha_inicio
        ).values('caalma', 'catd', 'canumdoc', 'casitgui')
        mapa_erp = {}
        for c in cabeceras_erp:
            pk = f"{c['caalma'].strip()}-{c['catd'].strip()}-{c['canumdoc'].strip()}"
            mapa_erp[pk] = c['casitgui']
    except Exception as e:
        logger.error(f"Error leyendo ERP para reconciliación: {e}")
        return

    cabeceras_local = LegacyMovAlmCab.objects.filter(empresa=empresa, cafecdoc__gt=fecha_inicio).values('id', 'caalma',
                                                                                                        'catd',
                                                                                                        'canumdoc',
                                                                                                        'casitgui')

    pks_actualizar = {}
    pks_borrar = []

    for c_loc in cabeceras_local:
        pk = f"{c_loc['caalma'].strip()}-{c_loc['catd'].strip()}-{c_loc['canumdoc'].strip()}"
        estado_erp = mapa_erp.get(pk)
        if estado_erp:
            if c_loc['casitgui'] != estado_erp: pks_actualizar[c_loc['id']] = estado_erp
        else:
            pks_borrar.append(c_loc['id'])

    # Aplicar Borrados
    if pks_borrar:
        cabs = LegacyMovAlmCab.objects.filter(id__in=pks_borrar)
        for c in cabs: LegacyMovAlmDet.objects.filter(empresa=empresa, dealma=c.caalma, detd=c.catd,
                                                      denumdoc=c.canumdoc).delete()
        cabs.delete()

    # Aplicar Updates (Simplificado: Solo estado para no hacer query pesada de nuevo, o full si es necesario)
    if pks_actualizar:
        for cid, nestado in pks_actualizar.items():
            LegacyMovAlmCab.objects.filter(id=cid).update(casitgui=nestado)


# ==========================================
# LÓGICA FASE 2 (Integrada desde Command)
# ==========================================

def procesar_legacy_data_logic(empresa, ahora, days_window):
    """
    Convierte datos Legacy a Movimientos/Stocks.
    Incluye lógica de Sedes y Regex.
    """

    # 1. Cargar Mapa de Sedes
    mapa_sedes_cache = {}
    try:
        mapa_sedes_cache['001'] = Almacen.objects.get(empresa=empresa, codigo='AL').id
        mapa_sedes_cache['002'] = Almacen.objects.get(empresa=empresa, codigo='AA').id
        mapa_sedes_cache['003'] = Almacen.objects.get(empresa=empresa, codigo='AD').id
    except Almacen.DoesNotExist:
        logger.warning("Faltan almacenes para mapeo de sedes.")

    fecha_corte = ahora - datetime.timedelta(days=days_window)

    query = Q(empresa=empresa, catd__in=TIPOS_DOC_RELEVANTES, cafecdoc__gte=fecha_corte)
    cabeceras = LegacyMovAlmCab.objects.filter(query).order_by('cafecdoc')

    productos_afectados = set()

    with transaction.atomic():
        for cab in cabeceras.iterator():

            # Anulados
            if cab.casitgui == 'A':
                pk_cab_anulada = f"{cab.caalma.strip()}-{cab.catd.strip()}-{cab.canumdoc.strip()}"
                MovimientoAlmacen.objects.filter(empresa=empresa, id_erp_cab=pk_cab_anulada).delete()
                continue

            # Validar Almacen Local
            try:
                alm_local = Almacen.objects.get(empresa=empresa, codigo=cab.caalma.strip())
            except Almacen.DoesNotExist:
                continue

            detalles = LegacyMovAlmDet.objects.filter(
                empresa=empresa, dealma=cab.caalma, detd=cab.catd, denumdoc=cab.canumdoc
            ).order_by('deitem')

            if not detalles.exists(): continue

            for det in detalles:
                cod_prod_raw = det.decodigo.strip() if det.decodigo else None
                if not cod_prod_raw or cod_prod_raw.upper() == 'TEXTO': continue

                try:
                    prod_local = Producto.objects.get(empresa=empresa, codigo_producto=cod_prod_raw)
                except Producto.DoesNotExist:
                    continue

                productos_afectados.add((alm_local.id, prod_local.id))

                pk_cab = f"{cab.caalma.strip()}-{cab.catd.strip()}-{cab.canumdoc.strip()}"
                pk_det = f"{pk_cab}-{det.deitem}"

                # Semáforo y Ejecución
                if cab.cacodmov == 'TD':
                    if cab.catipmov == 'I':
                        process_ingreso_traslado(empresa, cab, det, pk_cab, pk_det, alm_local, prod_local,
                                                 productos_afectados, ahora, mapa_sedes_cache)
                    else:
                        process_salida_traslado(empresa, cab, det, pk_cab, pk_det, alm_local, prod_local, ahora,
                                                mapa_sedes_cache)
                else:
                    process_movimiento_normal(empresa, cab, det, pk_cab, pk_det, alm_local, prod_local,
                                              mapa_sedes_cache)

    # Recálculo de Stock (Solo de afectados)
    for (aid, pid) in productos_afectados:
        try:
            Stock.recalcular_stock_completo(empresa.id, aid, pid)
        except Exception:
            pass


# --- HELPERS FASE 2 (Adaptados para Tasks) ---

def process_movimiento_normal(empresa, cab, det, pk_cab, pk_det, alm, prod, mapa_sedes_cache):
    doc_tipo = cab.catd.strip()
    cod_mov = (cab.cacodmov or '').strip()
    sit_gui = (cab.casitgui or '').strip()

    if doc_tipo == 'GS' and cod_mov == 'GF' and sit_gui == 'F': return
    if doc_tipo == 'NS' and cod_mov == 'AJ' and (det.decantid or 0) <= 0: return

    es_ingreso = (cab.catipmov == 'I')
    crear_movimiento_en_db(empresa, cab, det, pk_cab, pk_det, alm, prod, es_ingreso, mapa_sedes_cache)


def process_salida_traslado(empresa, cab, det, pk_cab, pk_det, alm, prod, ahora, mapa_sedes_cache):
    try:
        alm_destino = Almacen.objects.get(empresa=empresa, codigo=cab.carfalma.strip())
    except Almacen.DoesNotExist:
        return

    try:
        transf = Transferencia.objects.get(empresa=empresa, id_erp_salida_det=pk_det, producto=prod)
        transf.id_erp_salida_cab = pk_cab
        transf.almacen_origen = alm
        transf.cantidad_enviada = det.decantid or 0
        transf.fecha_envio = cab.cafecdoc

        if transf.id_erp_ingreso_det:
            limite = ahora - datetime.timedelta(days=DIAS_PARA_AUTO_RECEPCION)
            if cab.cafecdoc < limite:
                transf.estado = 'RECIBIDO'
                transf.cantidad_recibida = det.decantid
                transf.fecha_recepcion = transf.fecha_recepcion or cab.cafecdoc
        transf.save()
    except Transferencia.DoesNotExist:
        Transferencia.objects.create(
            empresa=empresa, id_erp_salida_det=pk_det, id_erp_salida_cab=pk_cab,
            almacen_origen=alm, almacen_destino=alm_destino, producto=prod,
            cantidad_enviada=det.decantid or 0, fecha_envio=cab.cafecdoc,
            estado='EN_TRANSITO'
        )

    crear_movimiento_en_db(empresa, cab, det, pk_cab, pk_det, alm, prod, False, mapa_sedes_cache)


def process_ingreso_traslado(empresa, cab, det, pk_cab, pk_det, alm, prod, productos_afectados, ahora,
                             mapa_sedes_cache):
    id_gs = f"{cab.carfalma.strip()}-{cab.carftdoc.strip()}-{cab.carfndoc.strip()}-{det.deitem}"
    try:
        alm_origen = Almacen.objects.get(empresa=empresa, codigo=cab.carfalma.strip())
    except Almacen.DoesNotExist:
        try:
            alm_origen = Almacen.objects.get(empresa=empresa, codigo='NA')
        except:
            alm_origen = alm

    transf, _ = Transferencia.objects.get_or_create(
        empresa=empresa, id_erp_salida_det=id_gs, producto=prod,
        defaults={
            'almacen_origen': alm_origen, 'almacen_destino': alm,
            'cantidad_enviada': det.decantid or 0, 'fecha_envio': cab.cafecdoc,
            'estado': 'EN_TRANSITO'
        }
    )
    transf.id_erp_ingreso_det = pk_det
    transf.id_erp_ingreso_cab = pk_cab
    transf.almacen_destino = alm

    debe_crear_movimiento = False
    limite = ahora - datetime.timedelta(days=DIAS_PARA_AUTO_RECEPCION)
    if cab.cafecdoc < limite:
        transf.estado = 'RECIBIDO'
        transf.cantidad_recibida = det.decantid
        transf.fecha_recepcion = cab.cafecdoc
        debe_crear_movimiento = True

    transf.save()
    productos_afectados.add((alm.id, prod.id))
    if debe_crear_movimiento:
        crear_movimiento_en_db(empresa, cab, det, pk_cab, pk_det, alm, prod, True, mapa_sedes_cache)


def crear_movimiento_en_db(empresa, cab, det, pk_cab, pk_det, alm, prod, es_ingreso, mapa_sedes_cache):
    item_val = det.deitem
    if item_val is None:
        try:
            item_val = int(pk_det.split('-')[-1])
        except:
            item_val = 0

    # Lógica de Sede Facturación (Regex)
    sede_facturacion_id = None
    if cab.catd.strip() == 'GS' and (cab.cacodmov or '').strip() == 'GV' and cab.casitgui == 'F':
        referencia = (cab.carfndoc or '').strip()
        if referencia and mapa_sedes_cache:
            match = re.search(r"^[A-Z]+([0-9]{3})", referencia)
            if match:
                sede_facturacion_id = mapa_sedes_cache.get(match.group(1))

    MovimientoAlmacen.objects.update_or_create(
        empresa=empresa, id_erp_det=pk_det,
        defaults={
            'id_erp_cab': pk_cab, 'almacen': alm, 'producto': prod,
            'es_ingreso': es_ingreso, 'almacen_ref': cab.carfalma,
            'tipo_documento_erp': cab.catd.strip(),
            'numero_documento_erp': det.denumdoc.strip(),
            'item_erp': item_val,
            'fecha_documento': cab.cafecdoc,
            'fecha_movimiento': cab.cafecact or cab.cafecdoc,
            'cantidad': det.decantid or 0,
            'costo_unitario': det.depreuni or 0, 'valor_total': det.devaltot or 0,
            'estado_erp': cab.casitgui,
            'glosa_cabecera': (cab.caglosa or '')[:500],
            'referencia_documento': cab.carfndoc,
            'sede_facturacion_id': sede_facturacion_id,  # <-- NUEVO
            'codigo_movimiento': (cab.cacodmov or '').strip(),
            'cliente_erp_id': (cab.cacodcli or '').strip(),
            'cliente_erp_nombre': (cab.canomcli or '').strip(),
            'nombre_proveedor': (cab.canompro or '').strip(),
            'direccion_envio_erp': (cab.cadirenv or '').strip(),
            'motivo_tras': (cab.motivo_gs or '').strip(),
            'state': True
        }
    )