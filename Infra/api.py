import json
import urllib.request
from typing import Dict, Any, List, Optional
from Core.interfaces import ICharacterSource


class GenshinApiSource(ICharacterSource):
    BASE_URL = "https://genshin.jmp.blue"

    def __init__(self, base_url: Optional[str] = None, timeout: float = 3.0):
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout

    def _get(self, path: str) -> Optional[Any]:
        try:
            req = urllib.request.Request(f"{self.base_url}{path}", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    def fetch(self, name: str) -> Optional[Dict[str, Any]]:
        data = self._get(f"/characters/{name.lower().strip()}")
        return data if isinstance(data, dict) and data.get("name") else None

    def list_names(self) -> List[str]:
        data = self._get("/characters")
        return list(data) if isinstance(data, list) else []


class StubCharacterSource(ICharacterSource):
    TEST_DATA: Dict[str, Dict[str, Any]] = {
        "diluc": {"name": "Diluc", "vision": "Pyro", "weapon": "Claymore", "rarity": 5,
                  "description": "Тестові дані: власник винокурні, майстер дворучного меча."},
        "venti": {"name": "Venti", "vision": "Anemo", "weapon": "Bow", "rarity": 5,
                  "description": "Тестові дані: бард, що керує вітром."},
        "zhongli": {"name": "Zhongli", "vision": "Geo", "weapon": "Polearm", "rarity": 5,
                    "description": "Тестові дані: консультант похоронного бюро."},
        "barbara": {"name": "Barbara", "vision": "Hydro", "weapon": "Catalyst", "rarity": 4,
                    "description": "Тестові дані: співачка і цілителька."},
        "fischl": {"name": "Fischl", "vision": "Electro", "weapon": "Bow", "rarity": 4,
                   "description": "Тестові дані: лучниця з вороном Озом."},
    }

    def fetch(self, name: str) -> Optional[Dict[str, Any]]:
        data = self.TEST_DATA.get(name.lower().strip())
        return dict(data) if data else None

    def list_names(self) -> List[str]:
        return list(self.TEST_DATA)


class FallbackCharacterSource(ICharacterSource):
    def __init__(self, primary: ICharacterSource, fallback: ICharacterSource):
        self.primary = primary
        self.fallback = fallback

    def fetch(self, name: str) -> Optional[Dict[str, Any]]:
        return self.primary.fetch(name) or self.fallback.fetch(name)

    def list_names(self) -> List[str]:
        return self.primary.list_names() or self.fallback.list_names()
