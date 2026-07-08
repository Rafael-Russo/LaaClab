"""Populate the database from the committed games fixture plus demo content.

Idempotent: games/genres are upserted; the demo user, library, forum threads,
comments and alerts are only created when missing, so re-running is safe. This
runs both locally and inside the Docker entrypoint.

    python manage.py seed
"""

import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from accounts.models import UserProfile
from alerts.models import Alert
from bugs.models import Bug, BugVote
from bugs.scoring import recompute_and_store
from catalog.models import Game, Genre, LibraryEntry
from community.models import GameComment, Reply, Topic
from core.models import Module

User = get_user_model()

# The fixture lives next to `fetch_steam` (see catalog/management/commands),
# which is what (re)generates it.
FIXTURE = Path(__file__).resolve().parents[3] / "catalog" / "fixtures" / "games_seed.json"

DEMO_USERNAME = "gamer"
DEMO_PASSWORD = "gamerpass123"

FAVORITE_HINTS = ("counter-strike", "valorant", "grand-theft", "apex", "call-of-duty")


class Command(BaseCommand):
    help = "Seed the database from the games fixture and add demo content."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("setup_permissions")
        self._seed_modules()
        games = self._seed_games()
        demo = self._seed_demo_user()
        self._seed_library(demo, games)
        self._seed_forum(games)
        self._seed_comments(games)
        self._seed_alerts(games)
        self._seed_bugs(games)
        for g in Game.objects.all():
            recompute_and_store(g)
        self.stdout.write(self.style.SUCCESS("Seed complete."))

    # -- modules ---------------------------------------------------------------

    def _seed_modules(self) -> None:
        names = {
            "catalog": "Catálogo",
            "community": "Comunidade",
            "alerts": "Alertas",
            "accounts": "Contas",
            "bugs": "BugoMetro",
        }
        for key, name in names.items():
            Module.objects.get_or_create(key=key, defaults={"name": name})
        self.stdout.write(f"  modules: {Module.objects.count()} registered")

    # -- games ---------------------------------------------------------------

    def _seed_games(self) -> dict[str, Game]:
        if not FIXTURE.exists():
            self.stderr.write(
                f"Fixture {FIXTURE} not found. Run `manage.py fetch_steam` first."
            )
            return {}

        records = json.load(open(FIXTURE, encoding="utf-8"))
        by_slug: dict[str, Game] = {}
        for rec in records:
            genre_names = rec.pop("genres", []) or []
            rec.pop("bug_score", None)
            slug = rec.get("slug") or slugify(rec["name"])[:140]
            rec["slug"] = slug

            lookup = (
                {"steam_appid": rec["steam_appid"]}
                if rec.get("steam_appid")
                else {"slug": slug}
            )
            game, _ = Game.objects.update_or_create(**lookup, defaults=rec)

            genres = [
                Genre.objects.get_or_create(slug=slugify(n), defaults={"name": n})[0]
                for n in genre_names
            ]
            if genres:
                game.genres.set(genres)
            by_slug[game.slug] = game

        self.stdout.write(f"  games: {Game.objects.count()} total")
        return by_slug

    # -- demo user -----------------------------------------------------------

    def _seed_demo_user(self) -> User:
        demo, _ = User.objects.get_or_create(
            username=DEMO_USERNAME,
            defaults={"email": "gamer@laaclab.local"},
        )
        # Always (re)set the documented demo password so login works after seed.
        demo.set_password(DEMO_PASSWORD)
        demo.save()
        # New users get a profile via signal; get_or_create also covers users
        # that predate the profile model.
        profile, _ = UserProfile.objects.get_or_create(user=demo)
        profile.handle = "Nikola98"
        profile.level = 12
        profile.xp = 1250
        profile.xp_max = 2000
        profile.bio = "Jogando, aprendendo e evoluindo todos os dias."
        profile.achievements = 24
        profile.friends = 8
        profile.days_active = 47
        profile.avatar_color = "#6b7cff"
        profile.save()
        self.stdout.write(f"  demo user: {DEMO_USERNAME} (password: {DEMO_PASSWORD})")
        return demo

    def _author(self, username: str) -> User:
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_unusable_password()
            user.save()
        return user

    # -- library -------------------------------------------------------------

    def _seed_library(self, demo: User, games: dict[str, Game]):
        if demo.library.exists():
            return
        for slug, game in games.items():
            LibraryEntry.objects.create(
                user=demo,
                game=game,
                favorite=any(h in slug for h in FAVORITE_HINTS),
            )
        self.stdout.write(f"  library: {demo.library.count()} entries")

    # -- forum ---------------------------------------------------------------

    def _seed_forum(self, games: dict[str, Game]):
        if Topic.objects.exists():
            return
        cs2 = self._find(games, "counter-strike")
        topics = [
            ("Flamezera", "Queda de FPS depois da última atualização", Topic.Type.DISCUSSION,
             "Depois da atualização de ontem, meu FPS caiu muito em todas as partidas. "
             "Alguém mais está passando por isso?"),
            ("rafaFPS", "Texturas não carregando no mapa inferno", Topic.Type.BUG,
             "Algumas texturas estão ficando pretas ou demorando pra carregar no inferno. "
             "Já verifiquei os arquivos e está tudo certo."),
            ("Leozin", "Comando para melhor desempenho", Topic.Type.TIP,
             "Descobri um comando que melhorou bastante meu desempenho, vou deixar aqui "
             "caso ajude alguém: -novid -nojoy -threads 4"),
        ]
        first = None
        for author, title, ttype, body in topics:
            topic = Topic.objects.create(
                game=cs2, author=self._author(author),
                title=title, type=ttype, body=body,
            )
            first = first or topic
        # A couple of replies on the first thread.
        for author, body in [
            ("Nikola98", "Mesmo problema aqui, achei que era só comigo."),
            ("ProPlayer_77", "Tenta limpar o cache de shaders, resolveu pra mim."),
        ]:
            Reply.objects.create(topic=first, author=self._author(author), body=body)
        self.stdout.write(f"  forum: {Topic.objects.count()} topics, {Reply.objects.count()} replies")

    # -- comments ------------------------------------------------------------

    def _seed_comments(self, games: dict[str, Game]):
        if GameComment.objects.exists():
            return
        game = self._find(games, "call-of-duty") or self._any(games)
        if not game:
            return
        for author in ("Joaozinho884", "MariaGamer", "ProPlayer_77"):
            GameComment.objects.create(
                game=game, author=self._author(author),
                text="eu achei o jogo muito superestimado blablablabla",
            )
        self.stdout.write(f"  comments: {GameComment.objects.count()}")

    # -- alerts --------------------------------------------------------------

    def _seed_alerts(self, games: dict[str, Game]):
        if Alert.objects.exists():
            return
        cod = self._find(games, "call-of-duty") or self._any(games)
        rows = [
            (cod, Alert.Severity.CRITICAL,
             "Instabilidade crítica nos servidores após atualização. "
             "Jogadores relatam desconexões e perda de progresso."),
            (cod, Alert.Severity.WARNING,
             "Quedas de FPS e travamentos em dispositivos de médio desempenho."),
            (cod, Alert.Severity.UPDATE,
             "Nova atualização disponível com melhorias gráficas e correções de falhas."),
            (self._find(games, "cyberpunk") or cod, Alert.Severity.CRITICAL,
             "Bugs de física reportados após o patch mais recente."),
        ]
        for game, severity, text in rows:
            if game:
                Alert.objects.create(game=game, severity=severity, text=text)
        self.stdout.write(f"  alerts: {Alert.objects.count()}")

    # -- bugs ------------------------------------------------------------------

    def _seed_bugs(self, games: dict[str, Game]):
        if Bug.objects.exists():
            return
        picks: list[Game] = []
        for needle in ("call-of-duty", "cyberpunk", "counter-strike"):
            game = self._find(games, needle)
            if game and game not in picks:
                picks.append(game)
        for game in games.values():
            if len(picks) >= 3:
                break
            if game not in picks:
                picks.append(game)
        if not picks:
            return

        # (title, category, severity, status) per game slot; index-aligned with `picks`.
        templates = [
            [
                ("Trava ao carregar o save após a atualização", Bug.Category.CRASH,
                 Bug.Severity.CRITICAL, Bug.Status.CONFIRMED),
                ("Queda de FPS em partidas longas", Bug.Category.PERFORMANCE,
                 Bug.Severity.HIGH, Bug.Status.CONFIRMED),
                ("Conquistas não desbloqueiam mesmo com os requisitos cumpridos",
                 Bug.Category.PROGRESSION, Bug.Severity.LOW, Bug.Status.OPEN),
            ],
            [
                ("Bugs de física após o patch mais recente", Bug.Category.GRAPHICS,
                 Bug.Severity.HIGH, Bug.Status.CONFIRMED),
                ("Desconexão constante dos servidores online", Bug.Category.ONLINE,
                 Bug.Severity.MEDIUM, Bug.Status.OPEN),
            ],
            [
                ("Texturas ficam pretas no mapa inferno", Bug.Category.GRAPHICS,
                 Bug.Severity.MEDIUM, Bug.Status.CONFIRMED),
                ("Perda de rank após queda de conexão", Bug.Category.ONLINE,
                 Bug.Severity.HIGH, Bug.Status.OPEN),
                ("Engasgos (stutter) ao trocar de arma", Bug.Category.PERFORMANCE,
                 Bug.Severity.LOW, Bug.Status.OPEN),
            ],
        ]

        voters = [self._author(n) for n in ("Joaozinho884", "MariaGamer", "ProPlayer_77", "Nikola98")]

        for game, bugs in zip(picks, templates, strict=False):
            for i, (title, category, severity, status) in enumerate(bugs):
                bug = Bug.objects.create(
                    game=game, title=title, category=category,
                    severity=severity, status=status,
                )
                for voter in voters[: i + 1]:
                    BugVote.objects.get_or_create(bug=bug, user=voter)
        self.stdout.write(f"  bugs: {Bug.objects.count()} (votes: {BugVote.objects.count()})")

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _find(games: dict[str, Game], needle: str) -> Game | None:
        for slug, game in games.items():
            if needle in slug:
                return game
        return None

    @staticmethod
    def _any(games: dict[str, Game]) -> Game | None:
        return next(iter(games.values()), None)
