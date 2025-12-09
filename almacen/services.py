# almacen/services.py
import datetime
from decimal import Decimal
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from .models import (
    MovimientoAlmacen, Transferencia, Stock,
    Empresa, Almacen, Producto, MovimientoAlmacenNota
)


# --- HELPERS DE FECHA (UTC PURO) ---
def make_utc_range_start(fecha):
    if not fecha: return None
    dt = datetime.datetime.combine(fecha, datetime.time.min)
    return dt.replace(tzinfo=datetime.timezone.utc)


def make_utc_range_end(fecha):
    if not fecha: return None
    dt = datetime.datetime.combine(fecha, datetime.time.max)
    return dt.replace(tzinfo=datetime.timezone.utc)


def get_stock_actual_rápido(empresa_id, almacen_id, producto_id):
    """
    Obtiene el stock actual rápido desde la tabla Stock.
    """
    try:
        stock = Stock.objects.get(
            empresa_id=empresa_id,
            almacen_id=almacen_id,
            producto_id=producto_id
        )
        return {
            'cantidad_actual': stock.cantidad_actual,
            'cantidad_en_transito': stock.cantidad_en_transito,
            'fecha_ultimo_movimiento': stock.fecha_ultimo_movimiento
        }
    except Stock.DoesNotExist:
        return {
            'cantidad_actual': 0,
            'cantidad_en_transito': 0,
            'fecha_ultimo_movimiento': None
        }


def _calcular_kardex_para_un_producto(empresa_id, almacen_id, producto_id, fecha_inicio, fecha_fin):
    """
    Calcula el Kárdex leyendo MovimientoAlmacen y enriqueciendo la data
    con las notas externas de MovimientoAlmacenNota.
    """

    if isinstance(fecha_inicio, datetime.datetime): fecha_inicio = fecha_inicio.date()
    if isinstance(fecha_fin, datetime.datetime): fecha_fin = fecha_fin.date()

    # Fechas UTC para evitar problemas de timezone
    utc_start = make_utc_range_start(fecha_inicio)
    utc_end = make_utc_range_end(fecha_fin)

    # =========================================================================
    # 1. CÁLCULO DE SALDO ANTERIOR
    # =========================================================================
    saldo_agg = MovimientoAlmacen.objects.filter(
        empresa_id=empresa_id,
        almacen_id=almacen_id,
        producto_id=producto_id,
        fecha_documento__lt=utc_start,
        state=True,
        estado_erp__in=['V', 'F', 'P']
    ).aggregate(
        ingresos=Coalesce(Sum('cantidad', filter=Q(es_ingreso=True)), Decimal('0'), output_field=DecimalField()),
        salidas=Coalesce(Sum('cantidad', filter=Q(es_ingreso=False)), Decimal('0'), output_field=DecimalField())
    )

    saldo_inicial = saldo_agg['ingresos'] - saldo_agg['salidas']

    # =========================================================================
    # 2. OBTENCIÓN DE DATOS (MOVIMIENTOS + NOTAS)
    # =========================================================================

    # A. Traemos los movimientos (Incluimos 'id_erp_cab' y 'glosa_detalle')
    movs = MovimientoAlmacen.objects.filter(
        empresa_id=empresa_id,
        almacen_id=almacen_id,
        producto_id=producto_id,
        fecha_documento__range=[utc_start, utc_end],
        state=True,
        estado_erp__in=['V', 'F']
    ).values(
        'id_erp_cab',  # <--- CLAVE PARA UNIR CON NOTAS
        'fecha_documento', 'tipo_documento_erp', 'numero_documento_erp',
        'es_ingreso', 'cantidad',
        'glosa_cabecera', 'glosa_detalle',  # Traemos ambas glosas
        'cliente_erp_nombre', 'nombre_proveedor',
        'referencia_documento', 'codigo_movimiento', 'almacen_ref'
    ).order_by('fecha_documento')

    # B. Traemos las Notas Externas (Optimización en memoria)
    # Extraemos IDs únicos de documentos
    ids_documentos = [m['id_erp_cab'] for m in movs if m['id_erp_cab']]

    # Consultamos la tabla satélite
    notas_qs = MovimientoAlmacenNota.objects.filter(
        empresa_id=empresa_id,
        id_erp_cab__in=ids_documentos
    ).values('id_erp_cab', 'texto_descripcion')

    # Mapeamos ID -> Texto { 'DOC-001': 'Nota importante...' }
    notas_map = {}
    for n in notas_qs:
        doc_id = n['id_erp_cab']
        texto = (n['texto_descripcion'] or '').strip()
        if texto:
            if doc_id in notas_map:
                notas_map[doc_id] += " " + texto  # Concatenar si hay múltiples líneas
            else:
                notas_map[doc_id] = texto

    # =========================================================================
    # 3. PROCESAMIENTO Y LÓGICA DE DETALLE
    # =========================================================================
    kardex_rows = []

    for m in movs:
        cod_mov = (m['codigo_movimiento'] or '').strip().upper()
        doc_id = m['id_erp_cab']

        # Recuperamos la nota externa si existe
        nota_externa = notas_map.get(doc_id, '')

        # Definimos la "Nota Real" con jerarquía:
        # 1. Nota Externa (Tabla Notas) -> 2. Glosa Detalle (Item) -> 3. Glosa Cabecera (Doc)
        texto_nota = nota_externa
        if not texto_nota:
            texto_nota = (m['glosa_detalle'] or '').strip()
        if not texto_nota:
            texto_nota = (m['glosa_cabecera'] or '').strip()

        # --- LÓGICA DE DESCRIPCIÓN ---

        if cod_mov == 'TD':
            detalle = m['glosa_cabecera'] or f"TRANSFERENCIA ENTRE ALMACENES - {m['almacen_ref']} "

        elif cod_mov == 'FT':
            # Ingreso por Flete: Proveedor + Nota
            proveedor = (m['cliente_erp_nombre'] or '').strip()
            partes = filter(None, [proveedor, texto_nota])
            detalle = " - ".join(partes)

            if not detalle: detalle = "REINGRESO POR NC"


        else:
            entidad = m['nombre_proveedor'] if m['es_ingreso'] else m['cliente_erp_nombre']
            partes = filter(None, [entidad, m['glosa_cabecera']])
            detalle = " - ".join(partes)

        # Construimos la fila
        kardex_rows.append({
            'fecha': m['fecha_documento'],
            'doc': f"{m['tipo_documento_erp']}-{m['numero_documento_erp']}",
            'ref': m['referencia_documento'],
            'entrada': m['cantidad'] if m['es_ingreso'] else 0,
            'salida': m['cantidad'] if not m['es_ingreso'] else 0,
            'detalle': detalle,
            'origen': 'ERP'
        })

    # =========================================================================
    # 4. CALCULAR SALDOS FINAL
    # =========================================================================

    # Ordenamos por fecha para asegurar consistencia en el cálculo de saldos
    kardex_rows.sort(key=lambda x: x['fecha'])

    reporte_final_producto = []

    # Fila 0: Saldo Anterior
    saldo_acumulado = saldo_inicial
    reporte_final_producto.append({
        'fecha': fecha_inicio,
        'doc': 'SALDO ANTERIOR',
        'entrada': 0,
        'salida': 0,
        'saldo': saldo_acumulado,
        'detalle': '---'
    })

    # Filas N: Movimientos
    for row in kardex_rows:
        entrada = row['entrada']
        salida = row['salida']
        saldo_acumulado += (entrada - salida)

        row['saldo'] = saldo_acumulado
        reporte_final_producto.append(row)

    return reporte_final_producto


def get_kardex_detallado(empresa_id, almacen_id, producto_ids, fecha_inicio, fecha_fin):
    """Genera el reporte consolidado."""

    reporte_consolidado = {}
    productos_validos = Producto.objects.filter(empresa_id=empresa_id, id__in=producto_ids)

    for producto in productos_validos:
        kardex_producto = _calcular_kardex_para_un_producto(
            empresa_id, almacen_id, producto.id, fecha_inicio, fecha_fin
        )

        # EXTRA: Calculamos el stock en tránsito para mostrarlo en el encabezado del reporte
        # Esto lee de Transferencia, pero NO se suma al Kárdex físico, es solo informativo.
        stock_transito = Transferencia.objects.filter(
            empresa_id=empresa_id,
            almacen_destino_id=almacen_id,  # Lo que viene HACIA mí
            producto_id=producto.id,
            estado='EN_TRANSITO'
        ).aggregate(
            total=Coalesce(Sum('cantidad_enviada'), Decimal('0'), output_field=DecimalField())
        )['total']

        reporte_consolidado[producto.id] = {
            "codigo_producto": producto.codigo_producto,
            "nombre_producto": producto.nombre_producto,
            "stock_en_transito": stock_transito,  # <--- Dato nuevo útil
            "kardex": kardex_producto
        }

    return reporte_consolidado
