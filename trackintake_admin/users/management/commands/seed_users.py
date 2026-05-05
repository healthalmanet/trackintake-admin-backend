from django.core.management.base import BaseCommand
from trackintake_admin.users.models import User
from django.utils import timezone
from datetime import timedelta
import random

USERS = [
    ("Aarav Sharma",    "aarav@example.com",   "Hero",   "Active"),
    ("Priya Mehta",     "priya@example.com",   "Basic",  "Inactive"),
    ("Rohan Verma",     "rohan@example.com",   "Silver", "Active"),
    ("Sneha Patel",     "sneha@example.com",   "Hero",   "Active"),
    ("Karan Singh",     "karan@example.com",   "Basic",  "Inactive"),
    ("Divya Nair",      "divya@example.com",   "Silver", "Active"),
    ("Amit Joshi",      "amit@example.com",    "Basic",  "Active"),
    ("Neha Gupta",      "neha@example.com",    "Hero",   "Inactive"),
    ("Rahul Kapoor",    "rahul@example.com",   "Free",   "Active"),
    ("Anjali Desai",    "anjali@example.com",  "Silver", "Active"),
    ("Vikram Rao",      "vikram@example.com",  "Hero",   "Active"),
    ("Pooja Iyer",      "pooja@example.com",   "Basic",  "Active"),
    ("Suresh Kumar",    "suresh@example.com",  "Free",   "Inactive"),
    ("Meera Pillai",    "meera@example.com",   "Silver", "Active"),
    ("Arjun Malhotra",  "arjun@example.com",   "Hero",   "Active"),
    ("Kavya Reddy",     "kavya@example.com",   "Basic",  "Active"),
    ("Nikhil Bose",     "nikhil@example.com",  "Free",   "Active"),
    ("Riya Chatterjee", "riya@example.com",    "Silver", "Inactive"),
    ("Deepak Tiwari",   "deepak@example.com",  "Hero",   "Active"),
    ("Simran Kaur",     "simran@example.com",  "Basic",  "Active"),
]

class Command(BaseCommand):
    help = "Seed database with sample users"

    def handle(self, *args, **kwargs):
        User.objects.all().delete()
        now = timezone.now()
        for i, (name, email, plan, status) in enumerate(USERS):
            User.objects.create(
                name=name,
                email=email,
                password="hashed_password_placeholder",
                weight=round(random.uniform(55, 90), 1),
                plan=plan,
                status=status,
                created_at=now - timedelta(days=random.randint(1, 60)),
            )
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(USERS)} users successfully."))
