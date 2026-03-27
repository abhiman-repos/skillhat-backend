from django.apps import AppConfig

class DbConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.db'

    def ready(self):
        from apps.db.mongo.connection import get_client
        try:
            get_client()
        except Exception as e:
            print("❌ MongoDB connection failed:", e)