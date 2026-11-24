# OOP_Practice_17 — Розгортання додатка (текстова гра)

Практичне заняття 17 з дисципліни «Об'єктно-орієнтоване програмування».
Виконала: Фізик Анна, КН-33, 3 курс.

Дизайн-документ: [DESIGN.md](DESIGN.md) (розгортання — розділ 13, графічний інтерфейс — розділ 11, збереження — розділ 6)

## Встановлення

### Спосіб 1. Готова програма для Windows (рекомендовано)

1. Відкрийте сторінку **Releases** цього репозиторію (праворуч на головній сторінці) і завантажте `TextGame-windows.zip`.
2. Розпакуйте архів у будь-яку папку.
3. Запустіть:
   * `TextGame.exe` — графічне вікно;
   * `TextGameConsole.exe` — консольна версія.

Python і бібліотеки встановлювати не потрібно: усе вже всередині exe.
Windows SmartScreen може попередити про невідомого видавця (файл не має цифрового підпису): «Докладніше» → «Виконати в будь-якому разі».

### Спосіб 2. Пакет Python (Windows, Linux, macOS)

Потрібен Python 3.10 або новіший.

```
pip install oop_text_game-1.0.0-py3-none-any.whl[gui]
textgame-gui        # графічне вікно
textgame            # консоль
```

Файл `.whl` лежить у тому самому релізі. Без `[gui]` встановлюється лише консольна версія.

### Спосіб 3. Один файл `.pyz`

Потрібен Python 3.10+. Консольна версія працює без жодних бібліотек:

```
python textgame.pyz
```

Графічна версія потребує PyQt6 (`pip install PyQt6`):

```
python textgame-gui.pyz
```

### Спосіб 4. З початкового коду

```
git clone https://github.com/ssvmaqwe/OOP_Practice_17.git
cd OOP_Practice_17
pip install -r requirements.txt
python gui.py        # або: python main.py
```

## Параметри запуску

| Параметр | Опис |
|---|---|
| `--version` | Показати версію і вийти |
| `--debug` | Режим налагодження: докладний журнал, помилки показуються повністю |
| `--data-dir=ПАПКА` | Зберігати дані в іншій папці |
| `<команда>` | (консоль) виконати одну команду і вийти, напр. `textgame enemies` |

Дані гри (персонажі, збереження, журнал `textgame.log`) зберігаються в `%APPDATA%\OOPTextGame` на Windows або `~/.local/share/oop-text-game` на Linux. Команда `storage` показує точний шлях.

## Збирання

### Windows (exe)

```
build_windows.bat
```

Скрипт встановлює залежності з `requirements-dev.txt`, запускає тести, збирає `dist\TextGame.exe` і `dist\TextGameConsole.exe` через PyInstaller і пакує їх у `dist\TextGame-windows.zip`.

### Linux / macOS (wheel, pyz, виконувані файли)

```
./build.sh
```

### Автоматично (GitHub Actions)

Workflow `.github/workflows/build.yml` запускається після кожного push у `main`. Він проганяє тести на Linux і Windows, збирає wheel, `.pyz` і exe та зберігає їх як artifacts.
Під час публікації **Release** ті самі файли автоматично додаються до релізу.

## Тести

```
pip install pytest
python -m pytest
```
