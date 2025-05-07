# accounts/roles.py
from rolepermissions.roles import AbstractUserRole

class ImportacionesAdmin(AbstractUserRole):
    # Aquí los permisos de “reports” (módulo)…
    available_permissions = {
        'importaciones':True,
        'importaciones.ver_fletes_internacionales':  True,
        'importaciones.registrar_flete_internacional':    True,
        'importaciones.ver_reporte_flete':True,
        'importaciones.ver_reporte_estibas': True,
    }

class ImportacionesAsis(AbstractUserRole):
    available_permissions = {
        'importaciones.ver_fletes_internacionales': True,
    }

class accountsAdmin(AbstractUserRole):
    available_permissions = {
        'user.listar_usuarios':  True,
        'user.registrar_usuario':   True,
        'user.editar_usuario':True,
    }

class accountsUser(AbstractUserRole):
    available_permissions = {
        'user.editar_perfil':True,
    }

class proveedor(AbstractUserRole):
    available_permissions = {
        'proveedor.cargar_documentos':True,
    }