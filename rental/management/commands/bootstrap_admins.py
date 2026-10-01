import os

from django.contrib.auth import get_user_model, password_validation
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create deployment administrator accounts from protected environment variables."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        account_count = 0
        for index in range(1, 4):
            username = os.environ.get(f"DJANGO_ADMIN_{index}_USERNAME", "").strip()
            password = os.environ.get(f"DJANGO_ADMIN_{index}_PASSWORD", "")
            if not username and not password:
                continue
            if not username or not password:
                raise CommandError(f"Both DJANGO_ADMIN_{index}_USERNAME and DJANGO_ADMIN_{index}_PASSWORD must be set together.")
            if User.objects.filter(username=username).exists():
                existing = User.objects.get(username=username)
                if not existing.is_superuser:
                    raise CommandError(f"Account {username!r} exists but is not a superuser; refusing to change it.")
                self.stdout.write(f"Administrator {username!r} already exists; leaving its password unchanged.")
                continue
            user = User(username=username, is_staff=True, is_superuser=True)
            password_validation.validate_password(password, user=user)
            user.set_password(password)
            user.save()
            account_count += 1
            self.stdout.write(self.style.SUCCESS(f"Created administrator {username!r}."))

        if not account_count:
            self.stdout.write("No new deployment administrators configured.")
