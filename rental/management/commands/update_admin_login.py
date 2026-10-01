import os

from django.contrib.auth import get_user_model, password_validation
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Rename a superuser and set its password from DJANGO_ADMIN_PASSWORD."

    def add_arguments(self, parser):
        parser.add_argument("current_username")
        parser.add_argument("new_username")

    def handle(self, *args, **options):
        User = get_user_model()
        password = os.environ.get("DJANGO_ADMIN_PASSWORD")
        if not password:
            raise CommandError("Set DJANGO_ADMIN_PASSWORD in the environment before running this command.")
        current_username = options["current_username"]
        new_username = options["new_username"]
        try:
            user = User.objects.get(username=current_username, is_superuser=True)
        except User.DoesNotExist as exc:
            raise CommandError(f"No superuser account exists with username {current_username!r}.") from exc
        if User.objects.exclude(pk=user.pk).filter(username=new_username).exists():
            raise CommandError(f"Username {new_username!r} is already in use.")

        user.username = new_username
        password_validation.validate_password(password, user=user)
        user.set_password(password)
        user.save(update_fields=["username", "password"])
        user.refresh_from_db()
        if not user.check_password(password):
            raise CommandError("Password verification failed after saving the account.")
        self.stdout.write(self.style.SUCCESS(f"Updated superuser login: {current_username} → {new_username}"))
