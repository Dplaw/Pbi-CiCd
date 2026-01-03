import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping


def _to_path(path: Path | str) -> Path:
    return path if isinstance(path, Path) else Path(path)


def read_text(path: Path | str, encoding: str = "utf-8") -> str:
    path = _to_path(path)
    return path.read_text(encoding=encoding)


def write_text(path: Path | str, text: str, encoding: str = "utf-8") -> None:
    path = _to_path(path)
    path.write_text(text, encoding=encoding)


def load_json(path: Path | str) -> Dict[str, Any]:
    path = _to_path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path | str, data: Dict[str, Any]) -> None:
    path = _to_path(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


@lru_cache(maxsize=None)
def _load_data_cached(path_str: str) -> Dict[str, Any]:
    path = Path(path_str)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_data(path: Path | str) -> Dict[str, Any]:
    return _load_data_cached(str(path))


def get_nested(mapping: Mapping, *keys: str, default: Any = None) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current


def ensure_platform_structure(platform: Dict[str, Any]) -> Dict[str, Any]:
    platform.setdefault("config", {})
    platform.setdefault("metadata", {})
    return platform


def log(msg: str) -> None:
    print(msg, flush=True)


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr, flush=True)
    raise SystemExit(code)


def require_env(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        die(f"Missing required env var: {name}")
    return val