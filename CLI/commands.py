from typing import Callable, Optional
from CLI.presenter import BaseCommandStrategy, Command, Args, CLI
from Core.characters import CharacterManager, CharacterProfile, CharacterService
from Core.combatant import CombatantFactory, EnemyLibrary
from Core.game import Game
from Core.actions import GameRuleError
from Core.skills import SkillLibrary
from Core.stats import Stats
from Core.saves import SaveManager, ProfileStorage, SaveError, SaveInfo, DEFAULT_SLOT, BUILTIN
from Infra.display import (CLIGraphic, ProfileConsoleRenderer, GameConsoleRenderer,
                           HistoryConsoleRenderer)

DEFAULT_ENEMIES = ["goblin", "slime"]
STATUS_NAMES = {"idle": "—", "active": "Триває", "won": "Перемога", "lost": "Поразка"}
SOURCE_NAMES = {BUILTIN: "вбудований", "custom": "власний", "api": "API"}


def format_save(info: SaveInfo) -> str:
    when = info.saved_at.replace("T", " ")[:19]
    return f"«{info.slot}» від {when}, крок {info.turn}, {STATUS_NAMES.get(info.status, info.status)}"


class CatalogStrategy(BaseCommandStrategy):
    def __init__(self, manager: CharacterManager, service: CharacterService,
                 storage: ProfileStorage, cli: CLI, reader: Callable[[str], str] = input):
        super().__init__()
        self.manager = manager
        self.service = service
        self.storage = storage
        self.cli = cli
        self.read = reader
        self.renderer = ProfileConsoleRenderer()

        self.register_command(Command("list", "Список персонажів у каталозі", self._cmd_list))
        self.register_command(Command("show", "Деталі персонажа (show <id>)", self._cmd_show))
        self.register_command(Command("create", "Створити власного персонажа (зберігається одразу)", self._cmd_create))
        self.register_command(Command("import", "Завантажити персонажа з API (import <name>)", self._cmd_import))
        self.register_command(Command("sources", "Імена, доступні для імпорту", self._cmd_sources))
        self.register_command(Command("delete", "Видалити власного персонажа (delete <id>)", self._cmd_delete))
        self.register_command(Command("save", "Примусово зберегти каталог персонажів", self._cmd_save))

    def _persist(self) -> bool:
        try:
            self.storage.save()
            return True
        except OSError as e:
            print(f"[Помилка збереження] {e}")
            return False

    def _cmd_list(self, args: Args) -> bool:
        profiles = self.manager.get_all()
        if not profiles:
            print("Каталог порожній.")
            return True
        print(CLIGraphic.banner("КАТАЛОГ ПЕРСОНАЖІВ"))
        rows = [[p.id, p.name, p.char_class, str(p.stats.health), str(p.stats.damage),
                 str(p.stats.magic), str(p.stats.armor), str(p.stats.speed), SOURCE_NAMES.get(p.source, p.source)]
                for p in profiles]
        print(CLIGraphic.table(["ID", "Ім'я", "Клас", "HP", "Шкода", "Магія", "Броня", "Шв.", "Тип"], rows))
        return True

    def _cmd_show(self, args: Args) -> bool:
        if not args.params:
            print("Вкажіть ID (напр. show warrior_1)")
            return True
        profile = self.manager.get_character(args.params[0])
        if not profile:
            print("Не знайдено.")
            return True
        profile.use_renderer(self.renderer)
        self.cli.display(profile)
        return True

    def _ask_int(self, prompt: str, default: int) -> int:
        raw = self.read(f"{prompt} [{default}]: ").strip()
        return int(raw) if raw else default

    def _cmd_create(self, args: Args) -> bool:
        print(CLIGraphic.banner("СТВОРЕННЯ ПЕРСОНАЖА"))
        char_id = self.read("ID: ").strip()
        name = self.read("Ім'я: ").strip()
        if not char_id or not name:
            print("ID та ім'я обов'язкові.")
            return True
        existing = self.manager.get_character(char_id)
        if existing and existing.source == BUILTIN:
            print("Цей ID зайнятий вбудованим персонажем.")
            return True
        classes = ", ".join(SkillLibrary.CLASS_SKILLS)
        char_class = self.read(f"Клас ({classes}): ").strip() or "Воїн"
        try:
            stats = Stats(
                health=self._ask_int("Здоров'я", 100),
                damage=self._ask_int("Шкода", 15),
                magic=self._ask_int("Магія", 5),
                armor=self._ask_int("Броня", 5),
                resist=self._ask_int("Резист, %", 10) / 100,
                speed=self._ask_int("Швидкість", 100),
            )
        except ValueError:
            print("Характеристики мають бути числами!")
            return True
        if stats.health <= 0 or stats.speed <= 0:
            print("Здоров'я та швидкість мають бути більшими за 0.")
            return True
        gfx_url = self.read("Графіка (URL): ").strip() or "default.png"
        self.manager.add_character(CharacterProfile(char_id, name, char_class, stats, gfx_url=gfx_url))
        if self._persist():
            print(f"Персонажа {name} створено і збережено. Навички: {', '.join(SkillLibrary.for_class(char_class))}.")
        return True

    def _cmd_import(self, args: Args) -> bool:
        if not args.params:
            print("Вкажіть ім'я (напр. import diluc). Список: sources")
            return True
        try:
            profile = self.service.import_character(args.params[0])
        except LookupError as e:
            print(e)
            return True
        if self._persist():
            print(f"Імпортовано і збережено: {profile.name} [{profile.id}] — клас {profile.char_class}")
        return True

    def _cmd_sources(self, args: Args) -> bool:
        names = self.service.available_names()
        print("Доступні для імпорту: " + (", ".join(names) if names else "немає"))
        return True

    def _cmd_delete(self, args: Args) -> bool:
        if not args.params:
            print("Вкажіть ID (напр. delete my_hero).")
            return True
        try:
            self.storage.delete(args.params[0])
        except SaveError as e:
            print(f"[Неможливо] {e}")
            return True
        print("Персонажа видалено.")
        return True

    def _cmd_save(self, args: Args) -> bool:
        if self._persist():
            print(f"Каталог збережено (власних персонажів: {len(self.storage.user_profiles())}).")
        return True


class GameStrategy(BaseCommandStrategy):
    def __init__(self, game: Game, manager: CharacterManager, saves: SaveManager, cli: CLI):
        super().__init__()
        self.game = game
        self.manager = manager
        self.saves = saves
        self.cli = cli
        self.game_renderer = GameConsoleRenderer()
        self.history_renderer = HistoryConsoleRenderer()

        self.register_command(Command("play_start",
                                      "Почати бій (play_start <id> [<id>...] [--enemies=goblin,wolf])",
                                      self._cmd_start))
        self.register_command(Command("play_action", "Дія героя (play_action <дія> [ціль])", self._cmd_action))
        self.register_command(Command("play_status", "Стан бою і доступні дії", self._cmd_status))
        self.register_command(Command("play_history", "Історія кроків (play_history [--last=N])", self._cmd_history))
        self.register_command(Command("continue", "Продовжити з останнього збереження", self._cmd_continue))
        self.register_command(Command("game_save", f"Зберегти гру у слот (game_save [слот], типово {DEFAULT_SLOT})",
                                      self._cmd_save))
        self.register_command(Command("game_load", "Завантажити гру зі слоту (game_load [слот])", self._cmd_load))
        self.register_command(Command("saves", "Список збережень", self._cmd_saves))
        self.register_command(Command("save_delete", "Видалити збереження (save_delete <слот>)", self._cmd_save_delete))
        self.register_command(Command("enemies", "Список типів ворогів", self._cmd_enemies))
        self.register_command(Command("skills", "Довідник навичок", self._cmd_skills))

    def _print_records(self, records) -> None:
        for r in records:
            prefix = f"[Крок {r.turn}] " if r.actor != "system" else ""
            print(f"{prefix}{r.text}")

    def autosave(self) -> None:
        try:
            self.saves.autosave(self.game)
        except (OSError, SaveError) as e:
            print(f"[Автозбереження не вдалося] {e}")

    def _cmd_start(self, args: Args) -> bool:
        if not args.params:
            print("Вкажіть ID персонажів (напр. play_start warrior_1).")
            return True
        heroes = []
        for i, pid in enumerate(args.params, start=1):
            profile = self.manager.get_character(pid)
            if not profile:
                print(f"Персонажа '{pid}' не знайдено.")
                return True
            heroes.append(CombatantFactory.from_profile(profile, f"h{i}"))
        enemy_ids = [e for e in args.flags.get("enemies", ",".join(DEFAULT_ENEMIES)).split(",") if e]
        unknown = [e for e in enemy_ids if not EnemyLibrary.exists(e)]
        if unknown:
            print(f"Невідомі вороги: {', '.join(unknown)}. Див. 'enemies'.")
            return True
        enemies = [CombatantFactory.from_template(t, f"e{i}") for i, t in enumerate(enemy_ids, start=1)]
        self.game = Game(self.game.calculator, self.game.behavior)
        print(CLIGraphic.banner("ТЕКСТОВА ГРА"))
        self._print_records(self.game.start(heroes, enemies))
        self.autosave()
        self._cmd_status(args)
        return True

    def _cmd_action(self, args: Args) -> bool:
        if not args.params:
            print("Вкажіть дію (напр. play_action attack e1).")
            return True
        target = args.params[1] if len(args.params) > 1 else None
        try:
            records = self.game.act(args.params[0], target)
        except GameRuleError as e:
            print(f"[Неможливо] {e}")
            return True
        self._print_records(records)
        self.autosave()
        if self.game.is_active:
            actor = self.game.current_actor
            print(f"\nХід героя: {actor.name} ({actor.uid}). 'play_status' — деталі.")
        else:
            print(f"\nГру завершено. Рахунок: {self.game.score}")
        return True

    def _cmd_status(self, args: Args) -> bool:
        self.game.use_renderer(self.game_renderer)
        self.cli.display(self.game)
        return True

    def _cmd_history(self, args: Args) -> bool:
        records = self.game.all_records()
        last: Optional[str] = args.flags.get("last")
        if last and last.isdigit():
            turns = sorted({r.turn for r in records})[-int(last):]
            records = [r for r in records if r.turn in turns]
        print(CLIGraphic.banner("ІСТОРІЯ БОЮ"))
        print(self.history_renderer.render(records))
        return True

    def _load_slot(self, slot: str) -> bool:
        try:
            self.game = self.saves.load(slot, self.game.calculator, self.game.behavior)
        except SaveError as e:
            print(f"[Неможливо] {e}")
            return False
        print(f"Гру відновлено зі слоту «{slot}».")
        self._cmd_status(Args("", "play_status", [], {}))
        return True

    def _cmd_continue(self, args: Args) -> bool:
        latest = self.saves.latest()
        if latest is None:
            print("Збережень ще немає. Почніть гру: play_start <id>.")
            return True
        print(f"Останнє збереження: {format_save(latest)}")
        self._load_slot(latest.slot)
        return True

    def _cmd_save(self, args: Args) -> bool:
        slot = args.params[0] if args.params else DEFAULT_SLOT
        try:
            info = self.saves.save(self.game, slot)
        except SaveError as e:
            print(f"[Неможливо] {e}")
            return True
        except OSError as e:
            print(f"[Помилка запису] {e}")
            return True
        print(f"Збережено: {format_save(info)}")
        return True

    def _cmd_load(self, args: Args) -> bool:
        if not args.params:
            return self._cmd_continue(args)
        self._load_slot(args.params[0])
        return True

    def _cmd_saves(self, args: Args) -> bool:
        saves = self.saves.list_saves()
        if not saves:
            print("Збережень немає.")
            return True
        print(CLIGraphic.banner("ЗБЕРЕЖЕННЯ"))
        rows = [[s.slot + (" (авто)" if s.is_auto else ""), s.saved_at.replace("T", " ")[:19], str(s.turn),
                 STATUS_NAMES.get(s.status, s.status), str(s.score), ", ".join(s.heroes)] for s in saves]
        print(CLIGraphic.table(["Слот", "Збережено", "Крок", "Статус", "Очки", "Герої"], rows))
        return True

    def _cmd_save_delete(self, args: Args) -> bool:
        if not args.params:
            print("Вкажіть слот (напр. save_delete slot1).")
            return True
        try:
            deleted = self.saves.delete(args.params[0])
        except SaveError as e:
            print(f"[Неможливо] {e}")
            return True
        print("Збереження видалено." if deleted else "Такого збереження немає.")
        return True

    def _cmd_enemies(self, args: Args) -> bool:
        rows = []
        for tid in EnemyLibrary.ids():
            t = EnemyLibrary.describe(tid)
            s = t["stats"]
            rows.append([tid, t["name"], str(s.health), str(s.damage), str(s.magic),
                         str(s.armor), f"{int(s.resist * 100)}%", str(s.speed)])
        print(CLIGraphic.table(["ID", "Назва", "HP", "Шкода", "Магія", "Броня", "Резист", "Шв."], rows))
        return True

    def _cmd_skills(self, args: Args) -> bool:
        rows = [[s.skill_id, s.name, s.kind, str(s.power), str(s.cooldown), s.description]
                for s in SkillLibrary.all()]
        print(CLIGraphic.table(["ID", "Назва", "Тип", "Сила", "Перезар.", "Опис"], rows))
        return True


class SystemStrategy(BaseCommandStrategy):
    def __init__(self, cli: CLI, data_dir: str = ""):
        super().__init__()
        self.cli = cli
        self.data_dir = data_dir
        self.register_command(Command("help", "Довідка", self._cmd_help))
        self.register_command(Command("storage", "Де зберігаються дані гри", self._cmd_storage))
        self.register_command(Command("version", "Версія програми", self._cmd_version))

    def _cmd_help(self, args: Args) -> bool:
        print(CLIGraphic.banner("ДОВІДКА"))
        rows = [[selector, desc] for selector, desc in self.cli.get_all_commands().items()]
        rows.append(["exit", "Вийти"])
        print(CLIGraphic.table(["Команда", "Опис"], rows))
        return True

    def _cmd_version(self, args: Args) -> bool:
        from version import __version__, APP_TITLE, AUTHOR
        mode = "debug" if getattr(self.cli, "debug", False) else "release"
        print(f"{APP_TITLE} {__version__} ({mode}) — {AUTHOR}")
        return True

    def _cmd_storage(self, args: Args) -> bool:
        print(f"Папка даних: {self.data_dir}")
        print("  characters.json — власні та імпортовані персонажі")
        print("  saves/<слот>.json — збереження гри (autosave — автоматичне)")
        print("  textgame.log — журнал роботи програми")
        return True
