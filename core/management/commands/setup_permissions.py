"""Create the standard auth Groups and wire up their permissions.

Idempotent: safe to run repeatedly (e.g. on every ``seed``/deploy) — groups
are fetched-or-created and their permission set is always re-applied via
``.set()``, so re-running yields the same state.

    python manage.py setup_permissions
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


def _perm(codename: str, app_label: str) -> Permission:
    return Permission.objects.get(codename=codename, content_type__app_label=app_label)


class Command(BaseCommand):
    help = "Create the Administrador/Moderador/Usuário groups and assign permissions."

    def handle(self, *args, **options):
        forum_mod_perm = _perm("can_moderate_forum", "community")
        games_mod_perm = _perm("can_moderate_games", "catalog")

        community_crud = [
            _perm(f"{action}_{model}", "community")
            for model in ("topic", "reply", "gamecomment")
            for action in ("add", "change", "delete")
        ]
        catalog_crud = [
            _perm(f"{action}_{model}", "catalog")
            for model in ("game", "genre")
            for action in ("add", "change", "delete")
        ]
        alerts_crud = [
            _perm(f"{action}_alert", "alerts") for action in ("add", "change", "delete")
        ]

        admin, _ = Group.objects.get_or_create(name="Administrador")
        admin.permissions.set(
            [forum_mod_perm, games_mod_perm, *community_crud, *catalog_crud, *alerts_crud]
        )

        forum_mod, _ = Group.objects.get_or_create(name="Moderador de Fórum")
        forum_mod.permissions.set(
            [
                forum_mod_perm,
                _perm("change_topic", "community"),
                _perm("delete_topic", "community"),
                _perm("change_reply", "community"),
                _perm("delete_reply", "community"),
                _perm("change_gamecomment", "community"),
                _perm("delete_gamecomment", "community"),
            ]
        )

        games_mod, _ = Group.objects.get_or_create(name="Moderador de Jogos/Bugs")
        games_mod.permissions.set([games_mod_perm, _perm("change_game", "catalog")])

        # Default group for regular users: no moderation permissions.
        Group.objects.get_or_create(name="Usuário")

        self.stdout.write(self.style.SUCCESS("Permission groups configured."))
