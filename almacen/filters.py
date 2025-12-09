import django_filters
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, time
from .models import MovimientoAlmacen,Stock,Almacen
from importaciones.models import Producto
import datetime as dt_module


class MovimientoAlmacenFilter(django_filters.FilterSet):
    # --- 1. FILTROS ESPECÍFICOS ---

    # Mapeamos el param url 'numero_documento' al campo del modelo 'numero_documento_erp'
    numero_documento = django_filters.CharFilter(
        field_name='numero_documento_erp',
        lookup_expr='icontains',
        label='Número Documento ERP'
    )

    # Agregamos Orden de Compra también, ya que vi que lo tienes en el modelo
    orden_compra = django_filters.CharFilter(
        field_name='numero_orden_compra',
        lookup_expr='icontains'
    )

    # --- 2. TUS MÉTODOS DE FECHA (Sin cambios) ---
    fecha_documento_desde = django_filters.DateFilter(
        field_name='fecha_documento', method='filter_utc_desde'
    )
    fecha_documento_hasta = django_filters.DateFilter(
        field_name='fecha_documento', method='filter_utc_hasta'
    )

    # --- 3. BÚSQUEDA GLOBAL ---
    search = django_filters.CharFilter(method='global_search', label='Buscar Global')

    class Meta:
        model = MovimientoAlmacen
        # Definimos los campos exactos
        fields = {
            'empresa': ['exact'],
            'almacen': ['exact'],
            'producto': ['exact','in'],
            'tipo_documento_erp': ['exact', 'in'],
            'es_ingreso': ['exact'],
            'proveedor_erp_id': ['exact'],
            'cliente_erp_id': ['exact'],
        }

    def global_search(self, queryset, name, value):
        """
        Busca el valor en:
        1. Número de documento ERP
        2. Nombre del producto
        3. Número de Orden de Compra
        4. Referencia
        5. Nombre del Cliente
        """
        if not value:
            return queryset

        return queryset.filter(
            Q(numero_documento_erp__icontains=value) |
            Q(producto__nombre_producto__icontains=value) |
            Q(numero_orden_compra__icontains=value) |
            Q(referencia_documento__icontains=value) |
            Q(cliente_erp_nombre__icontains=value)
        )

    # --- TUS MÉTODOS AUXILIARES (Sin cambios) ---
    def filter_utc_desde(self, queryset, name, value):
        if not value: return queryset
        dt = datetime.combine(value, time.min).replace(tzinfo=dt_module.timezone.utc)
        return queryset.filter(**{f"{name}__gte": dt})

    def filter_utc_hasta(self, queryset, name, value):
        if not value: return queryset
        dt = datetime.combine(value, time.max).replace(tzinfo=dt_module.timezone.utc)
        return queryset.filter(**{f"{name}__lte": dt})


class ProductoFilter(django_filters.FilterSet):
    # --- Filtros de texto ---
    # Usamos 'icontains' para que la búsqueda sea parcial y no sensible
    # a mayúsculas/minúsculas (ej. "sem" encontrará "Semilla")
    nombre_producto = django_filters.CharFilter(
        field_name='nombre_producto',
        lookup_expr='icontains'
    )
    codigo_producto = django_filters.CharFilter(
        field_name='codigo_producto',
        lookup_expr='icontains'
    )
    proveedor_marca = django_filters.CharFilter(
        field_name='proveedor_marca',
        lookup_expr='icontains'
    )

    # --- Filtro de ForeignKey ---
    # Para 'empresa', 'django-filter' es lo suficientemente inteligente
    # para saber que debe aceptar un ID (ej. ?empresa=5)

    class Meta:
        model = Producto
        # Lista de campos por los que permitimos filtrar
        fields = ['nombre_producto', 'codigo_producto', 'proveedor_marca', 'empresa']


class StockFilter(django_filters.FilterSet):
    """
    Filtros para el endpoint de Stock.
    """
    # Filtro para buscar por nombre o código de producto
    search = django_filters.CharFilter(method='filter_search_producto', label='Buscar por Producto (Código o Nombre)')

    # Filtro para stock positivo
    solo_con_stock = django_filters.BooleanFilter(method='filter_solo_con_stock')

    class Meta:
        model = Stock
        fields = {
            'empresa': ['exact'],  # /api/almacen/stock/?empresa=1
            'almacen': ['exact'],  # /api/almacen/stock/?almacen=2
            'producto': ['exact'],
        }

    def filter_search_producto(self, queryset, name, value):
        if not value:
            return queryset
        # Busca en los campos relacionados del modelo Producto
        return queryset.filter(
            Q(producto__codigo_producto__icontains=value) |
            Q(producto__nombre_producto__icontains=value)
        )

    def filter_solo_con_stock(self, queryset, name, value):
        if value:  # Si el filtro es ?solo_con_stock=true
            return queryset.filter(cantidad_actual__gt=0)
        return queryset


