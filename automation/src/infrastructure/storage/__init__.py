from pathlib import Path

from automation.src.domain.exceptions import MandatoryFieldError

from .excel_repository import append as append_excel
from .json_repository import (
    candidate_exists,
    candidate_filename,
    candidate_path,
    get_candidate,
    get_field,
    load,
    save,
    save_candidate,
    save_signature_link,
    update,
)

__all__ = [
    "append_excel",
    "get_field",
    "load",
    "read_signature_link",
    "save",
    "save_signature_link",
    "update",
    "candidate_exists",
    "candidate_filename",
    "candidate_path",
    "get_candidate",
    "save_candidate",
]


def read_signature_link(json_path: Path) -> tuple[str, str]:
    data = load(json_path)
    link = (data.get("zapsign", {}).get("link_assinatura") or "").strip()
    if not link:
        raise MandatoryFieldError(
            "zapsign.link_assinatura ausente no JSON. Rode 'assinatura' antes de 'finalizar'."
        )
    nome = (data.get("nome_completo") or "").strip() or "Candidato"
    return link, nome
