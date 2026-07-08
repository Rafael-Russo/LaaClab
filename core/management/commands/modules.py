"""Inspect and toggle feature modules from the command line.

    python manage.py modules --list
    python manage.py modules --enable community
    python manage.py modules --disable alerts
"""

from django.core.management.base import BaseCommand

from core.models import Module


class Command(BaseCommand):
    help = "List, enable or disable feature modules (core.Module)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--list", action="store_true", help="List all known modules."
        )
        parser.add_argument("--enable", metavar="KEY", help="Enable the given module.")
        parser.add_argument("--disable", metavar="KEY", help="Disable the given module.")

    def handle(self, *args, **options):
        if options["enable"]:
            self._set_enabled(options["enable"], True)
        if options["disable"]:
            self._set_enabled(options["disable"], False)
        if options["list"] or not (options["enable"] or options["disable"]):
            self._list()

    def _set_enabled(self, key: str, enabled: bool) -> None:
        module, _ = Module.objects.get_or_create(key=key, defaults={"name": key})
        module.enabled = enabled
        module.save()
        state = "enabled" if enabled else "disabled"
        self.stdout.write(self.style.SUCCESS(f"{key}: {state}"))

    def _list(self) -> None:
        modules = Module.objects.all()
        if not modules:
            self.stdout.write("No modules registered yet.")
            return
        for module in modules:
            state = "on" if module.enabled else "off"
            self.stdout.write(f"{module.key:12} {state:4} {module.name}")
