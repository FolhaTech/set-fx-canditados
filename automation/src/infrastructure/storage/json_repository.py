import json
import re
import time
from pathlib import Path
from typing import Any
from unicodedata import category, normalize

from automation.src.config import settings
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
    update(
        path,
        {
            "zapsign": {
                "link_assinatura": link,
                "capturado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        },
    )


def get_field(path: Path, field: str, required: bool = False) -> str | None:
    data = load(path)
    value = data.get(field)

    if required and not value:
        from automation.src.domain.exceptions import MandatoryFieldError

        raise MandatoryFieldError(f"Campo '{field}'")

    return str(value).strip() if value else None


def _slugify(text: str) -> str:
    if not text:
        return "candidato"

    text = normalize("NFD", text)
    text = "".join(ch for ch in text if category(ch) != "Mn")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "_", text).strip("_")

    return text or "candidato"


def candidate_filename(processo_id: str, nome: str) -> str:
    return f"{processo_id}_{_slugify(nome)}.json"


def candidate_path(processo_id: str, nome: str) -> Path:
    p = settings.PROJECT_ROOT / "dados"
    p.mkdir(parents=True, exist_ok=True)
    return p / candidate_filename(processo_id, nome)


def save_candidate(processo_id: str, nome: str, data: dict) -> Path:
    path = candidate_path(processo_id, nome)
    save(path, data)
    return path


def get_candidate(processo_id: str) -> dict | None:
    p = settings.PROJECT_ROOT / "dados"
    if not p.exists():
        return None

    for path in p.glob(f"{processo_id}_*.json"):
        return load(path)

    return None


def candidate_exists(processo_id: str) -> bool:
    p = settings.PROJECT_ROOT / "dados"
    if not p.exists():
        return False

    return any(p.glob(f"{processo_id}_*.json"))
