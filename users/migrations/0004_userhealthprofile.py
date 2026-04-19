from django.db import migrations


class Migration(migrations.Migration):
    """
    UserHealthProfile uses managed=False (existing table).
    This migration is intentionally empty to avoid conflicts.
    """

    dependencies = [
        ('users', '0003_userprofile_delete_user'),
    ]

    operations = []
