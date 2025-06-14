from django.core.management.commands.runserver import naiveip_re
from django.urls import path, include
from pandas.conftest import names
from rest_framework.routers import DefaultRouter
from .views import listar_importaciones, registrar_despacho, buscar_orden_importacion, upload_file, upload_file_excel, \
    buscar_proveedor, generar_reporte_base, generar_reporte_detallado, listar_estiba, listar_despachos, \
    listar_data_despacho, descargar_pdf, DespachoDeleteView, generar_reporte_base_bd, ListarDeclaracionesView, \
    DescargarZipView, EliminarDocumentoView, DocumentosPorDeclaracionView, DescargarDocumentoView, \
    ListarDeclaracionesDelUsuarioView, DocumentosPorDeclaracionUsuarioLogeadoView, DocumentoVisualizarView, obtener_pdf, \
    EditarPDFView, CombinarPDFsDeclaracionView, AgregarDocumentosExistentesAPIView, ReordenarPaginasAPIView, \
    DocumentosRelacionadosAPIView, AsignarPaginasAPIView, ListarExpedientesDeclaracionView, \
    ListarExpedientesAgrupadosView, ListarDocumentosPorTipoView, EliminarExpedienteDeclaracionView, \
    ActualizarMesAnioFiscalView, ActualizarFolioExpedienteView, TipoDocumentoViewSet, \
    DescargarDocumentosUnificadosPDFView, ActualizarEmpresaExpedienteView
from .views import CargaDirectaView, ProcesarArchivoComprimidoView, AsignarDeclaracionDesdeComprimidoView
from .views import ProcesarArchivoView,GuardarArchivoView
from graphene_django.views import GraphQLView
from .schema import schema


router = DefaultRouter()
router.register(r'tipo-documentos', TipoDocumentoViewSet, basename='tipo-documento')

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

    path("listar_archivos/", ListarExpedientesAgrupadosView.as_view()),
    path("listar_declaraciones/", ListarDeclaracionesView.as_view()),
    path("listar_declaraciones_por_usuario/", ListarDeclaracionesDelUsuarioView.as_view()),
    path('descargar_zip/<str:numero>/<int:anio>/', DescargarZipView.as_view(), name='descargar_zip'),
    path('documentos_por_declaracion/<str:numero>/<int:anio>/', DocumentosPorDeclaracionView.as_view()),
    path("listar_documentos_expediente_por_tipo/<int:declaracion_id>/", ListarDocumentosPorTipoView.as_view()),
    path('expedientes/eliminar_documento/<int:pk>/', EliminarExpedienteDeclaracionView.as_view(), name='eliminar_documento_expediente'),
    path('documentos_por_declaracion_usuario/<str:numero>/<int:anio>/', DocumentosPorDeclaracionUsuarioLogeadoView.as_view()),
    path('descargar_documento/<int:documento_id>/', DescargarDocumentoView.as_view()),
    path("eliminar_documento/<int:pk>/", EliminarDocumentoView.as_view()),
    path('documentos/<int:pk>/visualizar/', DocumentoVisualizarView.as_view(), name='documento_visualizar_seguro'),
    path('documentos/<int:pk>/', obtener_pdf, name='obtener-pdf'),
    path('documentos/<int:pk>/editar-pdf/', EditarPDFView.as_view(), name='editar_pdf'),
    path("documentos/<int:numero>/<int:anio>/combinar-pdfs/",CombinarPDFsDeclaracionView.as_view(),name="combinar_pdfs_declaracion"),
    path("documentos/<int:expediente_id>/agregar-documentos/",AgregarDocumentosExistentesAPIView.as_view(),name="agregar_documentos_existentes"),
    path("documentos/<int:expediente_id>/reordenar-paginas/",ReordenarPaginasAPIView.as_view(),name="reordenar_paginas"),
    path('documentos-relacionados/<int:documento_id>/', DocumentosRelacionadosAPIView.as_view(),name='documentos-relacionados'),
    path("documentos/asignar-paginas/", AsignarPaginasAPIView.as_view(), name="asignar-paginas"),
    path('expedientes/<int:declaracion_id>/actualizar_fiscal/', ActualizarMesAnioFiscalView.as_view(),name='actualizar_mes_anio_fiscal'),
    path('expedientes/<int:pk>/actualizar-folio/', ActualizarFolioExpedienteView.as_view(), name='actualizar_folio_expediente'),
    path('expedientes/<int:declaracion_id>/actualizar-empresa/', ActualizarEmpresaExpedienteView.as_view(), name='actualizar_empresa_expediente'),
    path("expedientes/<int:declaracion_id>/descargar_unificado/", DescargarDocumentosUnificadosPDFView.as_view()),
]




