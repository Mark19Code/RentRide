import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create superuser accounts with one-time generated passwords."

    def add_arguments(self, parser):
        parser.add_argument("usernames", nargs="+", help="One or more usernames to create")

    def handle(self, *args, **options):
        User = get_user_model()
        usernames = options["usernames"]
        duplicates = sorted({name for name in usernames if usernames.count(name) > 1})
        existing = sorted(User.objects.filter(username__in=usernames).values_list("username", flat=True))
        if duplicates or existing:
            conflicts = sorted(set(duplicates + existing))
            raise CommandError("These usernames already exist or were repeated: " + ", ".join(conflicts))

        for username in usernames:
            password = secrets.token_urlsafe(20)
            User.objects.create_superuser(username=username, password=password)
            self.stdout.write(self.style.SUCCESS(username + " — temporary password: " + password))

        self.stdout.write("These accounts have full Django superuser access. Share passwords privately and have each person change theirs in Settings.")
