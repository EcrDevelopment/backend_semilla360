#almacen/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import *

router = DefaultRouter()
router.register(r'gremisiones', GremisionCabViewSet, basename='gremisiones')
router.register(r'empresas', EmpresaViewSet, basename='empresa')
router.register(r'almacenes', AlmacenViewSet, basename='almacenes')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'movimientos', MovimientoAlmacenViewSet, basename='movimiento-almacen')
router.register(r'movimiento-notas', MovimientoAlmacenNotaViewSet, basename='movimiento-almacen-nota') # Opcional
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'transferencias', TransferenciaViewSet, basename='transferencia') # API de Transferencias

urlpatterns = [
    path("consulta-guia/", GremisionConsultaView.as_view(), name="gremision-consulta"),
    path('trigger-sync/', TriggerSyncAPIView.as_view(), name='trigger-sync'), # API del Botón
    path('check-sync-status/', CheckSyncStatusAPIView.as_view(), name='check-sync-status'),
    path('reporte-kardex/', KardexReportView.as_view(), name='api_reporte_kardex'),
]
# Agregar también las rutas del router
urlpatterns += router.urls