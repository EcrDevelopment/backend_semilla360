from collections import defaultdict
import django_rq
from rq.registry import StartedJobRegistry
from rest_framework import viewsets, permissions, status , mixins,filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
import random
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend # Para los filtros
from rest_framework.filters import OrderingFilter
from .filters import MovimientoAlmacenFilter, ProductoFilter, StockFilter
from .services import get_stock_actual_rápido, get_kardex_detallado
import requests
from .serializers import *
from .utils import *
import logging

logger = logging.getLogger(__name__)


class GremisionCabViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        empresa = request.query_params.get("empresa")
        if not empresa:
            return Response(
                {"error": "Debe indicar empresa en el parámetro ?empresa="},
                status=400
            )

        mapping = {
            "semilla": "bd_semilla_starsoft",
            "maxi": "bd_maxi_starsoft",
            "trading": "bd_trading_starsoft",
        }

        db_alias = mapping.get(empresa.lower())
        if not db_alias:
            return Response({"error": f"Empresa '{empresa}' no válida"}, status=400)

        data = GremisionCab.objects.using(db_alias).all()
        serializer = GremisionCabSerializer(data, many=True)
        return Response(serializer.data)


class GremisionConsultaView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        empresa = request.query_params.get("empresa")
        serie = request.query_params.get("grenumser")
        numero = request.query_params.get("grenumdoc")

        if not empresa:
            return Response({"error": "Debe indicar empresa en ?empresa="}, status=400)

        numero = numero.zfill(7)

        if not empresa:
            return Response({"error": f"la bd '{empresa}' no es válida"}, status=400)
        # --- FIN CORRECCIÓN ---

        try:
            cabecera = GremisionCab.objects.using(empresa).get(  # <-- USAR db_alias
                serie=serie,
                numero=numero
            )
        except GremisionCab.DoesNotExist:
            return Response({"error": "No se encontró el documento"}, status=404)

        detalles = GremisionDet.objects.using(empresa).filter(  # <-- USAR db_alias
            grenumser=cabecera.serie,
            grenumdoc=cabecera.numero,
        )

        cabecera_data = GremisionCabSerializer(cabecera).data
        detalles_data = GremisionDetSerializer(detalles, many=True).data

        return Response({
            "cabecera": cabecera_data,
            "detalles": detalles_data
        }, status=200)

class EmpresaViewSet(viewsets.ModelViewSet):
    """
    API endpoint para ver y editar Empresas.
    """
    permission_classes = [AllowAny]
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer

class AlmacenViewSet(viewsets.ModelViewSet):
    """
    API endpoint para ver y editar Almacenes.
    """
    permission_classes = [AllowAny]
    queryset = Almacen.objects.all()
    serializer_class = AlmacenSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['empresa']

class ProductoViewSet(viewsets.ModelViewSet):
    """
    API endpoint para ver y editar Productos.
    """
    permission_classes = [AllowAny]
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductoFilter

class MovimientoAlmacenViewSet(viewsets.ReadOnlyModelViewSet): # Solo lectura
    """
    API endpoint para ver movimientos de almacén sincronizados.
    Permite filtros por empresa, almacen, producto, fechas, tipo, etc.
    Ej: /api/almacen/movimientos/?empresa=1&almacen=2&fecha_documento_desde=2025-10-01
    """

    serializer_class = MovimientoAlmacenSerializer
    permission_classes = [permissions.AllowAny] # O AllowAny si quieres que sea público
    filter_backends = [DjangoFilterBackend, OrderingFilter] # Activa filtros y ordenación
    filterset_class = MovimientoAlmacenFilter # Usa la clase de filtro que definimos
    ordering_fields = [
        'fecha_documento',
        'fecha_movimiento',
        'producto__nombre_producto',
        'cantidad',
        'estado_erp',
        'es_ingreso',
        'numero_documento_erp'
    ]
    ordering = ['-fecha_documento', '-id'] # Orden por defecto

    def get_queryset(self):
        """
        Queryset base optimizado. Usamos select_related para las
        claves foráneas directas (relaciones 1-a-1).
        """
        return MovimientoAlmacen.objects.filter(state=True).select_related(
            'empresa',
            'almacen',
            'producto'
        )

    #  MÉTODO 'list' SOBRESCRITO PARA OPTIMIZACIÓN N+1
    def list(self, request, *args, **kwargs):
        # 1. Obtener el queryset base filtrado (empresa, almacén, fechas, etc.)
        queryset = self.filter_queryset(self.get_queryset())

        # 2. Paginar el queryset ANTES de hacer la consulta de notas
        page = self.paginate_queryset(queryset)

        # Si no hay página (paginación desactivada) o no hay datos,
        # simplemente serializa y devuelve.
        if page is None or not page:
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        # 3. Preparar la consulta de notas (El "truco" de optimización)

        # Obtener las claves únicas (empresa, id_erp_cab) DE LA PÁGINA ACTUAL
        # Usamos un set para evitar duplicados
        cabecera_keys = set()
        for movimiento in page:  # 'page' aquí es la lista de objetos de la página
            cabecera_keys.add((movimiento.empresa_id, movimiento.id_erp_cab))

        # Crear un mapa (diccionario) para guardar las notas
        # defaultdict(list) crea una lista vacía para cualquier clave nueva
        notas_map = defaultdict(list)

        if cabecera_keys:
            # Construir una consulta Q compleja para buscar todas las notas
            # de esas cabeceras: (Q(empresa=1) & Q(id_erp_cab='A')) | (Q(empresa=2) & Q(id_erp_cab='B'))
            q_objects = Q()
            for emp_id, cab_id in cabecera_keys:
                q_objects |= Q(empresa_id=emp_id, id_erp_cab=cab_id)

            # 4. Ejecutar UNA SOLA consulta para todas las notas de esta página
            notas_queryset = MovimientoAlmacenNota.objects.filter(q_objects)

            # 5. Poblar el mapa
            for nota in notas_queryset:
                key = (nota.empresa_id, nota.id_erp_cab)
                notas_map[key].append(nota)  # Agrega el objeto nota a la lista

        # 6. Serializar, pasando el 'notas_map' en el contexto
        serializer = self.get_serializer(
            page,
            many=True,
            context={**self.get_serializer_context(), 'notas_map': notas_map}
        )

        # 7. Devolver la respuesta paginada estándar
        return self.get_paginated_response(serializer.data)

class MovimientoAlmacenNotaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para ver las notas/glosas asociadas a movimientos.
    Permite filtrar por id_erp_cab.
    Ej: /api/almacen/movimiento-notas/?id_erp_cab=AD-NI-0000001
    """
    serializer_class = MovimientoAlmacenNotaSerializer
    permission_classes = [permissions.AllowAny] # O AllowAny
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    # Filtros simples para notas
    filterset_fields = ['empresa', 'id_erp_cab', 'id_erp_det']
    ordering = ['id_erp_cab', 'item_erp']

    def get_queryset(self):
        return MovimientoAlmacenNota.objects.filter(state=True)

class StockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para ver el Stock actual (calculado).
    Es de solo lectura.
    """
    serializer_class = StockSerializer
    permission_classes = [permissions.IsAuthenticated]  # O AllowAny

    # Conectar filtros y ordenación
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = StockFilter
    ordering_fields = ['producto__nombre_producto', 'cantidad_actual', 'fecha_ultimo_movimiento']
    ordering = ['producto__nombre_producto']  # Ordenar por nombre de producto por defecto

    def get_queryset(self):
        """
        Sobrescribimos para optimizar.
        Usamos select_related para evitar N+1 queries al obtener
        los nombres de empresa, almacén y producto.
        """
        # No filtramos por state=True porque el modelo Stock no hereda de BaseModel
        return Stock.objects.all().select_related(
            'empresa',
            'almacen',
            'producto'
        )


class TriggerSyncAPIView(APIView):
    """
    Endpoint para iniciar una sincronización MASTER.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        empresa_alias = request.data.get('empresa_alias')
        if not empresa_alias:
            return Response({"error": "Se requiere 'empresa_alias'."}, status=status.HTTP_400_BAD_REQUEST)

        start_year = request.data.get('start_year', 2000)
        days = request.data.get('days', 15)

        try:
            queue = django_rq.get_queue('default')

            # Encolamos la tarea
            job = queue.enqueue(
                'almacen.tasks.sincronizar_empresa_erp_task', # Pasamos string para evitar import circular si lo hubiera
                empresa_alias=empresa_alias,
                start_year=start_year,
                reconciliation_days=days,
                user_id=request.user.id
            )

            return Response(
                {
                    "status": f"Sincronización iniciada para {empresa_alias}.",
                    "job_id": job.id # Retornamos el ID por si acaso
                },
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            logger.error(f"Error al encolar la tarea: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TransferenciaViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    """
    API para ver y gestionar Transferencias.
    - Lista (GET) con filtros potentes.
    - Detalle (GET /<id>/) para cualquier estado.
    - Recibir (POST /<id>/recibir/) para transferencias 'EN_TRANSITO'.
    """
    serializer_class = TransferenciaSerializer
    permission_classes = [permissions.IsAuthenticated]

    # --- CAMBIO CLAVE #1: Queryset sin filtro de estado ---
    def get_queryset(self):
        """
        ¡CORREGIDO!
        Ya no filtra por 'EN_TRANSITO' aquí.
        Devuelve TODAS las transferencias para que el filtro y la vista de
        detalle (retrieve) funcionen para CUALQUIER estado.
        """
        return Transferencia.objects.select_related(
            'empresa', 'almacen_origen', 'almacen_destino', 'producto'
        ).order_by('-fecha_envio')  # Mantenemos el orden por defecto

    # --- ¡AÑADIDO! ---
    # Habilitamos los filtros de DRF
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Permitir al frontend filtrar por: ?estado=EN_TRANSITO
    filterset_fields = {
        'estado': ['exact'],
        'almacen_origen': ['exact'],
        'almacen_destino': ['exact'],
        'fecha_envio': ['gte', 'lte'],  # Para rangos de fecha
    }

    # Permitir al frontend buscar por: ?search=CODIGO_PRODUCTO
    search_fields = [
        'producto__codigo_producto',
        'producto__nombre_producto',
        'id_erp_salida_cab'
    ]

    # Permitir al frontend ordenar por: ?ordering=fecha_envio
    ordering_fields = ['fecha_envio', 'estado', 'producto__codigo_producto']
    ordering = ['-fecha_envio']  # Orden por defecto

    # --- CAMBIO CLAVE #2: Acción 'recibir' limpia ---
    @action(detail=True, methods=['post'], serializer_class=RecepcionSerializer)
    def recibir(self, request, pk=None):  # <-- ¡ESTA ES LA FIRMA CORRECTA!
        """
        Endpoint para recibir mercadería de una transferencia.
        POST /api/almacen/transferencias/{id}/recibir/
        """
        transferencia = self.get_object()

        # 1. Validación de estado
        if transferencia.estado != 'EN_TRANSITO':
            return Response(
                {'error': f'Esta transferencia ya fue procesada (Estado: {transferencia.get_estado_display()}).'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Validar el body del request
        serializer = RecepcionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        datos = serializer.validated_data
        cantidad_recibida = datos.get('cantidad_recibida')
        notas = datos.get('notas_recepcion', '')

        try:
            # 3. Llamar a la lógica de negocio en el MODELO
            exito = transferencia.recibir_mercaderia(
                cantidad_recibida=cantidad_recibida,
                fecha_recepcion=timezone.now(),  # <-- La fecha se define y pasa AQUÍ
                notas=notas,
                auto_recepcion=False
            )

            if not exito:
                return Response({"error": "La transferencia ya fue procesada."}, status=status.HTTP_409_CONFLICT)

            # 4. Devolver la transferencia actualizada
            updated_serializer = TransferenciaSerializer(
                transferencia,
                context=self.get_serializer_context()
            )
            return Response(updated_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error al recibir transferencia {pk}: {e}", exc_info=True)
            return Response({"error": f"Error al recibir: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def revertir_recepcion(self, request, pk=None):
        """
        Endpoint para revertir una recepción errónea y devolver
        la transferencia al estado 'EN_TRANSITO'.
        POST /api/almacen/transferencias/{id}/revertir_recepcion/
        """
        transferencia = self.get_object()

        try:
            exito = transferencia.revertir_recepcion()

            if not exito:
                return Response(
                    {"error": "No se puede revertir una transferencia que ya está 'EN TRANSITO'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Devolver la transferencia actualizada (ahora 'EN_TRANSITO')
            updated_serializer = TransferenciaSerializer(
                transferencia,
                context=self.get_serializer_context()
            )
            return Response(updated_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error al REVERTIR transferencia {pk}: {e}", exc_info=True)
            return Response({"error": f"Error al revertir: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckSyncStatusAPIView(APIView):
    """
    Endpoint para consultar estado de sincronización.
    Recupera progreso desde Redis (Job Meta).
    """
    # ¡CRÍTICO! Debe ser IsAuthenticated para obtener request.user.id correctamente
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_id = request.user.id

        # Debe coincidir EXACTAMENTE con como se guardó en Redis (ruta completa)
        task_name = 'almacen.tasks.sincronizar_empresa_erp_task'

        queue = django_rq.get_queue('default')

        #print(f"\n[CheckStatus] Consultando para Usuario ID: {user_id}", flush=True)

        def verificar_job(job_id, source_name):
            try:
                job = queue.fetch_job(job_id)
                if not job:
                    return None

                # Debugging agresivo para saber por qué falla
                # print(f"  - Analizando Job {job_id} ({source_name}): Func={job.func_name}, UserArg={job.kwargs.get('user_id')}, Status={job.get_status()}")

                # 1. Validar Nombre de Función
                if job.func_name != task_name:
                    return None

                # 2. Validar Dueño (Usuario)
                job_user_id = job.kwargs.get('user_id')
                if job_user_id != user_id:
                    # print(f"    -> Descartado: Pertenece a user {job_user_id}, no a {user_id}")
                    return None

                # 3. Validar Estado
                status_job = job.get_status()
                if status_job in ['finished', 'failed', 'canceled', 'stopped']:
                    # print(f"    -> Descartado: Estado terminal ({status_job})")
                    return None

                # --- SI LLEGA AQUÍ, ES EL JOB CORRECTO ---

                # Refrescar metadata desde Redis por seguridad
                job.refresh()

                percent = job.meta.get('progress_percent', 0)
                msg = job.meta.get('progress_message', 'Sincronización en progreso...')

                #print(f"  [✅ MATCH] Job Encontrado! Progreso: {percent}% - Msg: {msg}", flush=True)

                return {
                    "is_syncing": True,
                    "message": msg,
                    "percent": percent
                }
            except Exception as e:
                #print(f"Error analizando job {job_id}: {e}")
                return None

        # 1. Revisar Started (En ejecución actualmente)
        registry = StartedJobRegistry(queue=queue)
        job_ids = registry.get_job_ids()
        # print(f"[CheckStatus] Jobs en ejecución (StartedRegistry): {len(job_ids)}")

        for job_id in job_ids:
            data = verificar_job(job_id, "Started")
            if data: return Response(data, status=status.HTTP_200_OK)

        # 2. Revisar Queued (Esperando worker)
        queued_ids = queue.get_job_ids()
        # print(f"[CheckStatus] Jobs en cola (Queued): {len(queued_ids)}")

        for job_id in queued_ids:
            data = verificar_job(job_id, "Queued")
            if data: return Response(data, status=status.HTTP_200_OK)

        #print("[CheckStatus] No se encontraron tareas activas para este usuario.", flush=True)
        return Response({"is_syncing": False}, status=status.HTTP_200_OK)


class KardexReportView(APIView):
    """
    Endpoint DETALLADO para obtener el reporte de Kárdex.
    Calcula el historial, puede ser más lento.
    ¡AHORA ACEPTA MÚLTIPLES 'producto_id' EN LOS QUERY PARAMS!
    """

    def get(self, request, *args, **kwargs):
        try:
            empresa_id = int(request.query_params.get('empresa_id'))
            almacen_id = int(request.query_params.get('almacen_id'))

            # --- ¡CAMBIO AQUÍ! ---
            # Usamos getlist para obtener todos los parámetros 'producto_id'
            producto_ids_str = request.query_params.getlist('producto_id')
            if not producto_ids_str:
                raise ValueError("Se requiere al menos un parámetro 'producto_id'.")

            # Convertimos todos los IDs a enteros
            producto_ids = [int(pid) for pid in producto_ids_str]
            # --- FIN DEL CAMBIO ---

            fecha_inicio_str = request.query_params.get('fecha_inicio')  # 'YYYY-MM-DD'
            fecha_fin_str = request.query_params.get('fecha_fin')  # 'YYYY-MM-DD'

            if not all([fecha_inicio_str, fecha_fin_str]):
                raise ValueError("Faltan parámetros de fecha.")

            fecha_inicio = datetime.datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()

        except (TypeError, ValueError, AttributeError) as e:
            return Response(
                {'error': f'Parámetros inválidos: {e}. Asegúrate de enviar IDs numéricos y fechas YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            nombre_empresa = "Empresa Desconocida"
            try:
                empresa_obj = Empresa.objects.get(pk=empresa_id)
                # Usa 'razon_social' o 'nombre_empresa' según tu modelo
                nombre_empresa = empresa_obj.razon_social
            except Empresa.DoesNotExist:
                pass

            # 1. Obtener la data cruda (Tu servicio actual)
            kardex_data = get_kardex_detallado(
                empresa_id, almacen_id, producto_ids, fecha_inicio, fecha_fin
            )

            # 2. Verificar si se pide exportación
            export_format = request.query_params.get('export_format')  # 'excel', 'pdf' o None

            if export_format == 'excel':
                return generate_kardex_excel(kardex_data, fecha_inicio, fecha_fin,nombre_empresa)

            elif export_format == 'pdf':
                context = {
                    'empresa_id': empresa_id,
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                    'almacen_id': almacen_id
                }
                return generate_kardex_pdf(kardex_data, context,nombre_empresa)

            # 3. Si no hay formato, retornamos JSON (Comportamiento original)
            return Response(kardex_data)

        except Exception as e:
            return Response(
                {'error': f'Error generando el reporte: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )





