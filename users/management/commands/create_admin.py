from django.core.management.base import BaseCommand
from users.models import UserProfile


class Command(BaseCommand):
    help = "Create an admin user"

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Admin email')
        parser.add_argument('--password', type=str, help='Admin password')
        parser.add_argument('--name', type=str, help='Admin full name')

    def handle(self, *args, **options):
        email = options.get('email') or 'mayankdoye49@gmail.com'
        password = options.get('password') or 'Mayank@@321'
        name = options.get('name') or 'Mayank Doye'

        # Check if admin already exists
        if UserProfile.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f"Admin with email {email} already exists"))
            return

        # Create admin user
        admin = UserProfile.objects.create(
            full_name=name,
            email=email,
            password=password,
            role="admin",
            is_active=True,
            is_admin=True,
            is_superuser=True
        )

        self.stdout.write(self.style.SUCCESS(f"✓ Admin user created successfully"))
        self.stdout.write(f"  Email: {admin.email}")
        self.stdout.write(f"  Name: {admin.full_name}")
        self.stdout.write(f"  Role: {admin.role}")
