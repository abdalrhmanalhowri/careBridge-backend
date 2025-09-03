import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from CareBridge.models import User

if not User.objects.filter(email="admin@example.com").exists():
    User.objects.create_superuser(
        email="admin@admin.com",
        password="12345",
        name="Admin"
    )
    print("Superuser created!")
else:
    print("Superuser already exists.")
