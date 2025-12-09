# almacen/tasks.py

import logging
import re
import datetime
from collections import defaultdict

from django_rq import job
from rq import get_current_job
from django.utils import timezone
from django.db import connections, transaction
from django.db.models import Q
from django.conf import settings
from django.core.paginator import Paginator
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# MODELOS
from .models import (
    MovAlmCab, MovAlmDet,
    LegacyMovAlmCab, LegacyMovAlmDet, ControlSyncMovAlmacen,
    MovimientoAlmacen, Transferencia, Stock, Almacen, MovimientoAlmacenNota
)
from importaciones.models import Empresa, Producto

logger = logging.getLogger(__name__)

TIPOS_DOC_RELEVANTES = ['NI', 'GS', 'TR', 'TK', 'NS', 'BV', 'NC', 'FT']
DIAS_PARA_AUTO_RECEPCION = 7


# ==========================================
# SECCIÓN 1: HELPERS
# ==========================================

def notificar_grupo_empresa(empresa_id, status, message, result=None):
    """Envía mensaje al WebSocket."""
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


def actualizar_progreso_job(percent_float, msg):
    """Guarda en Redis para recuperación (F5)."""
    try:
        job = get_current_job()
        if job:
            job.meta['progress_percent'] = percent_float
            job.meta['progress_message'] = msg
            job.save_meta()
    except Exception:
        pass


# ==========================================
# SECCIÓN 2: TAREA PRINCIPAL
# ==========================================

@job('default', timeout=7200)
def sincronizar_empresa_erp_task(empresa_alias, start_year=2000, reconciliation_days=30, user_id=None):
    ahora = timezone.now()
    db_alias = empresa_alias
    BATCH_SIZE = 50

    # 1. Validaciones
    try:
        if db_alias not in connections: raise Exception(f"Alias '{db_alias}' no configurado.")
        try:
            empresa = Empresa.objects.get(nombre_empresa=db_alias)
        except Empresa.DoesNotExist:
            raise Exception(f"Empresa '{db_alias}' no existe.")
    except Exception as e:
        return f"Error Config: {e}"

    notificar_grupo_empresa(empresa.id, 'started', f'Iniciando Sincronización...')

    try:
        # ---------------------------------------------------------
        # LÓGICA DE FECHAS "INTELIGENTE"
        # ---------------------------------------------------------
        # Fecha absoluta de inicio (ej: 2000-01-01)
        fecha_start_year = datetime.datetime(start_year, 1, 1, tzinfo=datetime.timezone.utc)

        control_sync, created = ControlSyncMovAlmacen.objects.get_or_create(
            empresa=empresa, defaults={'ultima_fecha': fecha_start_year}
        )

        # Fecha donde se quedó la última vez (Fase 1)
        ultima_sync_fecha = control_sync.ultima_fecha if not created else fecha_start_year

        if settings.USE_TZ and timezone.is_naive(ultima_sync_fecha):
            ultima_sync_fecha = timezone.make_aware(ultima_sync_fecha, datetime.timezone.utc)

        # Normalizamos
        ultima_sync_fecha = ultima_sync_fecha.replace(hour=0, minute=0, second=0)

        # Calculamos la fecha de seguridad (30 días atrás desde HOY)
        fecha_reconciliacion = ahora - datetime.timedelta(days=reconciliation_days)

        # --- EL CEREBRO DE LA LÓGICA ---
        # Si 'ultima_sync_fecha' es del año 2000, 'min' elegirá 2000 -> Fase 2 procesa todo.
        # Si 'ultima_sync_fecha' es de hoy, 'min' elegirá hace 30 días -> Fase 2 procesa reciente.
        fecha_inicio_fase2 = min(ultima_sync_fecha, fecha_reconciliacion)

        logger.info(f"Fase 1 desde: {ultima_sync_fecha}. Fase 2 desde: {fecha_inicio_fase2}")

        # ---------------------------------------------------------
        # FASE 1: EXTRACCIÓN (ERP -> Legacy)
        # ---------------------------------------------------------
        notificar_grupo_empresa(empresa.id, 'running_f1', 'Fase 1: Extrayendo datos...')

        qs_base = MovAlmCab.objects.using(db_alias).filter(
            Q(cafecdoc__gte=ultima_sync_fecha),
            catd__in=TIPOS_DOC_RELEVANTES
        ).order_by('cafecdoc')

        total_f1 = qs_base.count()

        if total_f1 > 0:
            paginator = Paginator(qs_base, BATCH_SIZE)
            processed_count = 0
            ultima_fecha_ok = None

            for page_num in paginator.page_range:
                page = paginator.page(page_num)
                batch_records = page.object_list

                # Prefetching Masivo
                q_filters = Q()
                for cab in batch_records:
                    q_filters |= Q(dealma=cab.caalma, detd=cab.catd, denumdoc=cab.canumdoc)

                remote_details = MovAlmDet.objects.using(db_alias).filter(q_filters).order_by('deitem')
                grouped_details = defaultdict(list)
                for d in remote_details:
                    grouped_details[(d.dealma, d.detd, d.denumdoc)].append(d)

                # Transacción de Escritura
                with transaction.atomic(using='default'):
                    for cab in batch_records:
                        key = (cab.caalma, cab.catd, cab.canumdoc)

                        cab_defaults = {
                            'cafecdoc': cab.cafecdoc, 'catipmov': cab.catipmov, 'cacodmov': cab.cacodmov,
                            'casitua': cab.casitua, 'carftdoc': cab.carftdoc, 'carfndoc': cab.carfndoc,
                            'casoli': cab.casoli, 'cafecdev': cab.cafecdev, 'cacodpro': cab.cacodpro,
                            'cacencos': cab.cacencos, 'carfalma': cab.carfalma, 'caglosa': cab.caglosa,
                            'cafecact': cab.cafecact, 'cahora': cab.cahora, 'causuari': cab.causuari,
                            'cacodcli': cab.cacodcli, 'canomcli': cab.canomcli, 'casitgui': cab.casitgui,
                            'canompro': cab.canompro, 'canomtra': cab.canomtra, 'cacodtran': cab.cacodtran,
                            'caimportacion': cab.caimportacion, 'canroimp': cab.canroimp,
                            'motivo_gs': cab.motivo_gs, 'canumord': cab.canumord, 'cadirenv': cab.cadirenv,
                        }
                        LegacyMovAlmCab.objects.update_or_create(
                            empresa=empresa, caalma=cab.caalma, catd=cab.catd,
                            canumdoc=cab.canumdoc, defaults=cab_defaults
                        )

                        LegacyMovAlmDet.objects.filter(
                            empresa=empresa, dealma=key[0], detd=key[1], denumdoc=key[2]
                        ).delete()

                        nuevos_detalles = [
                            LegacyMovAlmDet(
                                empresa=empresa, dealma=d.dealma, detd=d.detd, denumdoc=d.denumdoc,
                                deitem=d.deitem, decodigo=d.decodigo, decantid=d.decantid,
                                depreuni=d.depreuni, deserie=d.deserie, defecdoc=d.defecdoc,
                                deglosa=d.deglosa, delote=d.delote, deunidad=d.deunidad,
                                devaltot=d.devaltot, dedescri=d.dedescri, detexto=d.detexto
                            ) for d in grouped_details.get(key, [])
                        ]
                        LegacyMovAlmDet.objects.bulk_create(nuevos_detalles)
                        if cab.cafecdoc: ultima_fecha_ok = cab.cafecdoc

                processed_count += len(batch_records)

                # Progreso Fase 1 (0% - 50%)
                progreso_f1 = processed_count / total_f1
                percent_global = round(progreso_f1 * 50, 1)
                msg = f"Fase 1: {int(percent_global)}% ({processed_count}/{total_f1})"

                notificar_grupo_empresa(empresa.id, 'progress', msg,
                                        result={'percent': percent_global, 'phase': 'Fase 1'})
                actualizar_progreso_job(percent_global, msg)

                if ultima_fecha_ok:
                    control_sync.ultima_fecha = ultima_fecha_ok
                    control_sync.save(update_fields=['ultima_fecha'])
        else:
            actualizar_progreso_job(50, "Fase 1 (Al día)")

        # Reconciliación (Solo para la ventana reciente)
        reconciliar_datos_recientes_f1(empresa, db_alias, ahora, reconciliation_days)

        # ---------------------------------------------------------
        # FASE 2: PROCESAMIENTO (Legacy -> Final)
        # ---------------------------------------------------------
        logger.info(f"--- Fase 2 iniciando desde: {fecha_inicio_fase2} ---")

        # LLAMADA CORREGIDA: Pasamos la FECHA, no los días.
        procesar_legacy_data_logic(empresa, fecha_inicio_fase2, ahora)

    except Exception as e_main:
        logger.error(f"Error FATAL: {e_main}", exc_info=True)
        notificar_grupo_empresa(empresa.id, 'failed', str(e_main))
        return f"Error: {e_main}"

    notificar_grupo_empresa(empresa.id, 'finished', "Proceso Exitoso.", result="OK")
    actualizar_progreso_job(100, "Finalizado")
    return "OK"


# ==========================================
# SECCIÓN 3: LÓGICA INTERNA FASE 1
# ==========================================

def reconciliar_datos_recientes_f1(empresa, db_alias, ahora, dias_atras):
    """Detecta eliminaciones y cambios de estado (V->F, V->A) recientes."""
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
        logger.error(f"Error ERP Reconciliacion: {e}")
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

    if pks_borrar:
        cabs = LegacyMovAlmCab.objects.filter(id__in=pks_borrar)
        for c in cabs:
            LegacyMovAlmDet.objects.filter(empresa=empresa, dealma=c.caalma, detd=c.catd, denumdoc=c.canumdoc).delete()
        cabs.delete()

    if pks_actualizar:
        for cid, nestado in pks_actualizar.items():
            LegacyMovAlmCab.objects.filter(id=cid).update(casitgui=nestado)


# ==========================================
# SECCIÓN 4: LÓGICA INTERNA FASE 2
# ==========================================

def procesar_legacy_data_logic(empresa, fecha_inicio_proceso, ahora):
    """
    Versión corregida: Define pk_det dentro del bucle para evitar errores.
    """

    # 1. Mapa de Sedes
    mapa_sedes_cache = {}
    try:
        mapa_sedes_cache['001'] = Almacen.objects.get(empresa=empresa, codigo='AL').id
        mapa_sedes_cache['002'] = Almacen.objects.get(empresa=empresa, codigo='AA').id
        mapa_sedes_cache['003'] = Almacen.objects.get(empresa=empresa, codigo='AD').id
    except:
        pass

    # 2. Query
    query = Q(empresa=empresa, catd__in=TIPOS_DOC_RELEVANTES, cafecdoc__gte=fecha_inicio_proceso)
    cabeceras = LegacyMovAlmCab.objects.filter(query).order_by('cafecdoc')
    total_f2 = cabeceras.count()
    productos_afectados = set()

    if total_f2 == 0:
        actualizar_progreso_job(100, "Fase 2 (Sin datos)")
        return

    with transaction.atomic():
        for i, cab in enumerate(cabeceras.iterator()):

            # Notificación
            if (i + 1) % 50 == 0 or (i + 1) == total_f2:
                progreso_local = (i + 1) / total_f2
                percent_global = 50 + round(progreso_local * 50, 1)
                msg = f"Fase 2: {int(percent_global)}% ({i + 1}/{total_f2})"
                notificar_grupo_empresa(empresa.id, 'progress', msg,
                                        result={'percent': percent_global, 'phase': 'Fase 2'})
                actualizar_progreso_job(percent_global, msg)

            # --- LÓGICA DE CABECERA ---
            pk_cab = f"{cab.caalma.strip()}-{cab.catd.strip()}-{cab.canumdoc.strip()}"

            # A) Anulados
            if cab.casitgui == 'A':
                MovimientoAlmacen.objects.filter(empresa=empresa, id_erp_cab=pk_cab).delete()
                # También borramos notas asociadas si se anula
                MovimientoAlmacenNota.objects.filter(empresa=empresa, id_erp_cab=pk_cab).delete()
                continue

            # B) Validaciones Local
            try:
                alm_local = Almacen.objects.get(empresa=empresa, codigo=cab.caalma.strip())
            except Almacen.DoesNotExist:
                continue

            detalles = LegacyMovAlmDet.objects.filter(
                empresa=empresa, dealma=cab.caalma, detd=cab.catd, denumdoc=cab.canumdoc
            ).order_by('deitem')

            if not detalles.exists(): continue

            # --- BUCLE DE DETALLES ---
            for det in detalles:
                # ¡AQUÍ ES DONDE DEBE IR pk_det!
                pk_det = f"{pk_cab}-{det.deitem}"

                cod_prod_raw = det.decodigo.strip() if det.decodigo else None

                # 1. Lógica de NOTAS (TEXTO)
                if not cod_prod_raw or cod_prod_raw.upper() == 'TEXTO':
                    crear_nota_almacen(empresa, pk_cab, pk_det, det)
                    continue  # Saltamos al siguiente detalle, no procesamos como producto

                # 2. Lógica de PRODUCTOS
                try:
                    prod_local = Producto.objects.get(empresa=empresa, codigo_producto=cod_prod_raw)
                except Producto.DoesNotExist:
                    continue

                productos_afectados.add((alm_local.id, prod_local.id))

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

    # Recálculo
    if productos_afectados:
        notificar_grupo_empresa(empresa.id, 'running_f2', 'Finalizando: Recalculando Stock...')
        for (aid, pid) in productos_afectados:
            try:
                Stock.recalcular_stock_completo(empresa.id, aid, pid)
            except:
                pass


# --- HELPERS FASE 2 (Igual que antes) ---
def process_movimiento_normal(empresa, cab, det, pk_cab, pk_det, alm, prod, mapa_sedes_cache):
    doc_tipo = cab.catd.strip()
    cod_mov = (cab.cacodmov or '').strip()
    sit_gui = (cab.casitgui or '').strip()

    # Filtros de negocio para ignorar basura
    if doc_tipo == 'GS' and cod_mov == 'GF' and sit_gui == 'F': return
    if doc_tipo == 'NS' and cod_mov == 'AJ' and (det.decantid or 0) <= 0: return

    es_ingreso = (cab.catipmov == 'I')
    crear_movimiento_en_db(empresa, cab, det, pk_cab, pk_det, alm, prod, es_ingreso, mapa_sedes_cache)


def process_salida_traslado(empresa, cab, det, pk_cab, pk_det, alm, prod, ahora, mapa_sedes_cache):
    try:
        alm_destino = Almacen.objects.get(empresa=empresa, codigo=cab.carfalma.strip())
    except Almacen.DoesNotExist:
        return  # Si no existe destino local, no es transferencia interna válida

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
        except ValueError:
            pass
    # ---------------------------

    try:
        transf = Transferencia.objects.get(empresa=empresa, id_erp_salida_det=pk_det, producto=prod)
        transf.id_erp_salida_cab = pk_cab
        transf.almacen_origen = alm
        transf.cantidad_enviada = det.decantid or 0
        transf.fecha_envio = fecha_precisa  # <--- Usamos fecha con hora

        # Auto-Recepción si ya existe ingreso vinculado
        if transf.id_erp_ingreso_det:
            limite = ahora - datetime.timedelta(days=DIAS_PARA_AUTO_RECEPCION)
            # Comparamos fecha precisa vs limite
            if fecha_precisa < limite:
                transf.estado = 'RECIBIDO'
                transf.cantidad_recibida = det.decantid
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

    # Creamos el movimiento físico de SALIDA inmediatamente
    crear_movimiento_en_db(empresa, cab, det, pk_cab, pk_det, alm, prod, False, mapa_sedes_cache)


def process_ingreso_traslado(empresa, cab, det, pk_cab, pk_det, alm, prod, productos_afectados, ahora,
                             mapa_sedes_cache):
    """NI-TD (Entrada): Crea Transferencia. Solo crea Movimiento si Auto-Recepciona."""
    id_gs = f"{cab.carfalma.strip()}-{cab.carftdoc.strip()}-{cab.carfndoc.strip()}-{det.deitem}"

    try:
        alm_origen = Almacen.objects.get(empresa=empresa, codigo=cab.carfalma.strip())
    except Almacen.DoesNotExist:
        try:
            alm_origen = Almacen.objects.get(empresa=empresa, codigo='NA')
        except:
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
        except ValueError:
            pass
    # ---------------------------

    transf, created = Transferencia.objects.get_or_create(
        empresa=empresa, id_erp_salida_det=id_gs, producto=prod,
        defaults={
            'almacen_origen': alm_origen, 'almacen_destino': alm,
            'cantidad_enviada': det.decantid or 0,
            'fecha_envio': fecha_precisa,  # Fecha precisa
            'estado': 'EN_TRANSITO'
        }
    )
    transf.id_erp_ingreso_det = pk_det
    transf.id_erp_ingreso_cab = pk_cab
    transf.almacen_destino = alm

    debe_crear_movimiento = False
    limite = ahora - datetime.timedelta(days=DIAS_PARA_AUTO_RECEPCION)

    # Comparamos fecha precisa vs limite
    if fecha_precisa < limite:
        transf.estado = 'RECIBIDO'
        transf.cantidad_recibida = det.decantid
        transf.fecha_recepcion = fecha_precisa
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
        except ValueError:
            pass

    # 3. Guardado
    MovimientoAlmacen.objects.update_or_create(
        empresa=empresa, id_erp_det=pk_det,
        defaults={
            'id_erp_cab': pk_cab, 'almacen': alm, 'producto': prod,
            'es_ingreso': es_ingreso, 'almacen_ref': cab.carfalma,
            'tipo_documento_erp': cab.catd.strip(),
            'numero_documento_erp': det.denumdoc.strip(),
            'item_erp': item_val,
            'fecha_documento': fecha_precisa,  # <--- Fecha CON HORA
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
            'id_importacion':(cab.canroimp),
            'importacion':(cab.caimportacion),
            'proveedor_erp_id':cab.cacodpro,
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