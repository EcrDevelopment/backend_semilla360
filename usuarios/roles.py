# accounts/roles.py
from rolepermissions.roles import AbstractUserRole

class SystemAdmin(AbstractUserRole):
    available_permissions = {
        'mantenimiento.tabla_tipo_documentos':True,
    }

class ImportacionesAdmin(AbstractUserRole):
    available_permissions = {
        'importaciones':True,
        'importaciones.ver_fletes_internacionales':  True,
        'importaciones.registrar_flete_internacional':    True,
        'importaciones.ver_reporte_flete':True,
        'importaciones.ver_reporte_estibas': True,
        'importaciones.administrar_documentos_dua': True,
        'importaciones.administrar_expedientes_dua': True,
        'importaciones.editar_expedientes_dua': True,
        'importaciones.descargar_expedientes_dua': True,
        'importaciones.agregar_mes_expedientes_dua': True,
        'importaciones.agregar_empresa_expedientes_dua': True,
    }


class ImportacionesAsis(AbstractUserRole):
    available_permissions = {
        'importaciones.ver_fletes_internacionales': True,
        'importaciones.administrar_documentos_dua': True,
        'importaciones.administrar_expedientes_dua': True,
        'importaciones.editar_expedientes_dua': True,
        'importaciones.descargar_expedientes_dua': True,
        'importaciones.agregar_mes_expedientes_dua': True,
        'importaciones.agregar_empresa_expedientes_dua': True,
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
        'proveedor.administrar_documentos': True,
    }