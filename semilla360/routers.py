class DatabaseRouter:
    def db_for_read(self, model, **hints):
        """
        Determina la base de datos a usar para las operaciones de lectura.
        """
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Determina la base de datos a usar para las operaciones de escritura.
        """
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Permite relaciones entre modelos en la misma base de datos.
        """
        db_set = {'default', 'bd_semilla_starsoft', 'bd_maxi_starsoft', 'bd_trading_starsoft'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Restringe las migraciones a la base de datos `default`.
        """
        return db == 'default'
