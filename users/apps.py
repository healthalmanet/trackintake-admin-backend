from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
<<<<<<< HEAD

    def ready(self):
        import users.signals
=======
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
