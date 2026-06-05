import re
from typing import Optional

import unicodedata


# Text normalization
def normalize_text(s: Optional[str]) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^\w\s-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    return s


def clean_filename(name: Optional[str]) -> str:
    name = re.sub(r'[\/:*?"<>|]', "_", str(name or "").strip())
    return (
            name.replace(" ", "_") or "Candidato"
    )


def clean_value(value: Optional[str]) -> str:
    if not value:
        return ""

    s = str(value).strip()
    if s.lower() in ("- selecione algo -", "none", "null"):
        return ""

    return s


# Currency formatting
def format_currency(value: Optional[str]) -> str:
    value = clean_value(value)
    if value is None:
        return ""

    try:
        numero = float(value.replace(".", "").replace(",", "."))
        return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError,):
        return f"R$ {value}"


# Checkboxes
def is_checked(value: Optional[str]) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().lower().startswith("[x]")


def clean_checkbox(value: Optional[str]) -> str:
    if not isinstance(value, str):
        return ""
    return (
        value.replace("[x]", "")
        .replace("[X]", "")
        .replace("[ ]", "")
        .strip()
    )


# Validation
def validate_email(email: Optional[str]) -> bool:
    if not email:
        return False
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", str(email).strip()))


def validate_not_empty(value: Optional[str], field_name: str = "campo") -> str:
    cleaned = clean_value(value)
    if not cleaned:
        from .exceptions import MandatoryFieldError
        raise MandatoryFieldError(f"Campo obrigatório não preenchido: {field_name}")
    return cleaned
