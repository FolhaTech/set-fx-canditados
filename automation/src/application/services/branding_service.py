import json
from pathlib import Path

from automation.src.config import settings
from automation.src.domain.models import Enterprise

EMPRESA_TEMAS: dict[Enterprise, dict[str, str]] = {
    Enterprise.FOLHA_TECH: {
        "primaria": "#F58220",
        "secundaria": "#FFE8D1",
        "texto": "#333333",
    },
    Enterprise.GENTER: {
        "primaria": "#9E2F2A",
        "secundaria": "#F6E3E2",
        "texto": "#333333",
    },
    Enterprise.ARANTES: {
        "primaria": "#1D4ED8",
        "secundaria": "#DBEAFE",
        "texto": "#333333",
    },
}

ASSINATURA_POR_EMPRESA: dict[Enterprise, str] = {
    Enterprise.GENTER: "AssArimura.svg",
    Enterprise.ARANTES: "AssArimura.svg",
    Enterprise.FOLHA_TECH: "AssArimura.svg",
}


LOGO_POR_EMPRESA: dict[Enterprise, str] = {
    Enterprise.ARANTES: "logo-v2.png",
    Enterprise.GENTER: "logo.png",
    Enterprise.FOLHA_TECH: "logo.png",
}


def _load_signature_config() -> dict:
    config_path = settings.PROJECT_ROOT / "signatures.json"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_theme(empresa: Enterprise) -> dict[str, str]:
    return EMPRESA_TEMAS.get(empresa, EMPRESA_TEMAS[Enterprise.GENTER])


def find_logo(empresa: Enterprise) -> Path | None:
    pasta = settings.logos_dir_path / empresa.value
    if not pasta.exists():
        return None

    nome_arquivo = LOGO_POR_EMPRESA.get(empresa)
    if nome_arquivo:
        caminho = pasta / nome_arquivo
        if caminho.exists():
            return caminho

    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        arquivos = list(pasta.glob(ext))
        if arquivos:
            return arquivos[0]

    return None


def find_signature(empresa: Enterprise) -> Path | None:
    nome_arquivo = ASSINATURA_POR_EMPRESA.get(empresa)
    if not nome_arquivo:
        return None

    caminho = settings.assinaturas_dir_path / nome_arquivo
    return caminho if caminho.exists() else None


def find_signature_by_role(empresa: Enterprise, papel: str) -> Path | None:
    config = _load_signature_config()
    for _key, info in config.get("signatarios", {}).items():
        papeis = info.get("papeis_por_empresa", {}).get(empresa.value, [])
        if papel in papeis:
            caminho = settings.PROJECT_ROOT / info["arquivo"]
            if caminho.exists():
                return caminho
    return None


def find_all_signatures_for_company(empresa: Enterprise) -> dict[str, Path]:
    config = _load_signature_config()
    resultado: dict[str, Path] = {}

    for _key, info in config.get("signatarios", {}).items():
        papeis = info.get("papeis_por_empresa", {}).get(empresa.value, [])
        for papel in papeis:
            caminho = settings.PROJECT_ROOT / info["arquivo"]
            if not caminho.exists():
                continue
            base_key = papel
            candidate_key = base_key
            idx = 1
            while candidate_key in resultado:
                candidate_key = f"{base_key}_{idx}"
                idx += 1
            resultado[candidate_key] = caminho
    return resultado
