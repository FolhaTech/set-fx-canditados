import json
import time
from pathlib import Path
from typing import Any

from automation.src.domain import JsonNotFoundError


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise JsonNotFoundError(f"JSON não encontrado: {path}")

    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def update(path: Path, updates: dict[str, Any]) -> None:
    if path.exists():
        data = load(path)
    else:
        data = {}

    data.update(updates)
    save(path, data)


def save_signature_link(path: Path, link: str) -> None:
    update(path, {
        "zapsign": {
            "link_assinatura": link,
            "capturado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    })


def get_field(path: Path, field: str, required: bool = False) -> str | None:
    data = load(path)
    value = data.get(field)

    if required and not value:
        from automation.src.domain.exceptions import MandatoryFieldError
        raise MandatoryFieldError(f"Campo '{
        field
        }'")

    return str(value).strip() if value else None
