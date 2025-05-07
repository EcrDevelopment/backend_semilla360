from django.core.management.commands.runserver import naiveip_re
from django.urls import path, include
from pandas.conftest import names
from rest_framework.routers import DefaultRouter
from .views import listar_importaciones, registrar_despacho, buscar_orden_importacion, upload_file, upload_file_excel, \
    buscar_proveedor, generar_reporte_base, generar_reporte_detallado, listar_estiba, listar_despachos, \
    listar_data_despacho, descargar_pdf, DespachoDeleteView, generar_reporte_base_bd, ListarDeclaracionesView, \
    DescargarZipView, EliminarDocumentoView, DocumentosPorDeclaracionView, DescargarDocumentoView
from .views import CargaDirectaView, ProcesarArchivoComprimidoView, AsignarDeclaracionDesdeComprimidoView
from .views import ProcesarArchivoView,GuardarArchivoView
from graphene_django.views import GraphQLView
from .schema import schema


router = DefaultRouter()
urlpatterns = [
    path('', include(router.urls)),
    path('graphql/', GraphQLView.as_view(graphiql=True, schema=schema)),
    path('lista/', listar_importaciones, name='listar_importaciones'),
    path('buscar_oi/', buscar_orden_importacion, name='buscar_orden_importacion'),
    path('buscar_prov/', buscar_proveedor, name='buscar_proveedor'),
    path('generar_reporte/', generar_reporte_base, name='generar_reporte'),
    path('generar_reporte_detallado/', generar_reporte_detallado, name='generar_reporte'),
    path('registrar-despacho/', registrar_despacho, name='registrar_despacho'),
    path('listar-despachos/', listar_despachos, name='listar_despachos'),
    path('listar-data-despacho/', generar_reporte_base_bd, name='listar-data-despacho'),
    path('descargar_pdf/<int:despacho_id>/', descargar_pdf, name='descargar_pdf'),
    path('upload/', upload_file, name='upload_file'),
    path('upload-file-excel/', upload_file_excel, name='upload_file_excel'),
    path('generar-reporte-estiba/',listar_estiba,name='generar_reporte_estiba'),
    path('procesar_archivo/', ProcesarArchivoView.as_view(), name='procesar_archivo'),
    path('renombrar_carpetas/', GuardarArchivoView.as_view(), name='renombrar_carpetas'),
    path('despachos/<int:pk>/eliminar/', DespachoDeleteView.as_view(), name='eliminar_despacho'),
    path('carga_directa/', CargaDirectaView.as_view(),name='carga_directa'),
    path('procesar_comprimido/', ProcesarArchivoComprimidoView.as_view(),name='procesar_comprimido'),
    path("asignar_comprimido/", AsignarDeclaracionDesdeComprimidoView.as_view(),name='asignar_comprimido'),

    path("listar_declaraciones/", ListarDeclaracionesView.as_view()),
    path('descargar_zip/<str:numero>/<int:anio>/', DescargarZipView.as_view(), name='descargar_zip'),
    path('documentos_por_declaracion/<str:numero>/<int:anio>/', DocumentosPorDeclaracionView.as_view()),
    path('descargar_documento/<int:documento_id>/', DescargarDocumentoView.as_view()),
    path("eliminar_documento/<int:pk>/", EliminarDocumentoView.as_view()),
]


