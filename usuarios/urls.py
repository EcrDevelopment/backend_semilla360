#usuarios/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView
from . import views
from .views import *

urlpatterns = [
    path('auth/login/',CustomTokenObtainPairView.as_view(), name='login'),
    path('get-csrf-token/', views.get_csrf_token, name='get_csrf_token'),
    path('auth/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),  # Solicitar restablecimiento
    path('auth/password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),  # Confirmar restablecimiento

    path('content_types/', fetch_content_types, name='content_types'),
    # Usuarios
    path('usuarios', UserViewSet.as_view({'get': 'list', 'post': 'create'}), name='usuarios'),
    path('usuarios/<int:pk>', UserViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='usuario-detalle'),

    # Roles
    path('roles', RoleViewSet.as_view({'get': 'list', 'post': 'create'}), name='roles'),
    path('roles/<int:pk>', RoleViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='rol-detalle'),

    # Permisos
    path('permisos', PermissionViewSet.as_view({'get': 'list', 'post': 'create'}), name='permisos'),
    path('permisos/<int:pk>/', PermissionViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='permiso-detalle'),

    # Empresas
    path('empresas/', EmpresaListView.as_view(), name='empresa-list'),
    path('empresas/<int:pk>/', EmpresaDetailView.as_view(), name='empresa-detail'),

    # Direcciones
    path('direcciones/', DireccionListCreateView.as_view(), name='direccion-list-create'),
    path('direcciones/<int:pk>/', DireccionDetailView.as_view(), name='direccion-detail'),
    path('empresas/<int:empresa_id>/direcciones/', DireccionesPorEmpresaView.as_view(), name='empresa-direcciones'),

    # Departamentos, Provincias y Distritos
    path('departamentos/', DepartamentoListView.as_view(), name='departamento-list'),
    path('provincias/', ProvinciaListView.as_view(), name='provincia-list'),
    path('distritos/', DistritoListView.as_view(), name='distrito-list'),


]
