from django.apps import AppConfig


class UnsphereConfig(AppConfig):
    name = "unsphere"

    def ready(self):
        from django.db.backends.signals import connection_created

        def configure_sqlite(sender, connection, **kwargs):
            if connection.vendor != "sqlite":
                return
            pragmas = [
                "PRAGMA journal_mode = WAL",
                "PRAGMA busy_timeout = 5000",
                "PRAGMA foreign_keys = ON",
                "PRAGMA synchronous = NORMAL",  # safe with WAL, faster than FULL
                "PRAGMA cache_size = -64000",  # 64 MB page cache
                "PRAGMA temp_store = MEMORY",
                "PRAGMA mmap_size = 134217728",  # 128 MB memory-mapped I/O
            ]
            with connection.cursor() as cursor:
                for pragma in pragmas:
                    cursor.execute(pragma)

        connection_created.connect(configure_sqlite)
