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
    Enterprise.GENTER: "AssArimura.png",
    Enterprise.ARANTES: "AssRapha.png",
    Enterprise.FOLHA_TECH: "AssFernando.png",
}


def get_theme(empresa: Enterprise) -> dict[str, str]:
    return EMPRESA_TEMAS.get(empresa, EMPRESA_TEMAS[Enterprise.GENTER])


def find_logo(empresa: Enterprise) -> Path | None:
    pasta = settings.logos_dir_path / empresa.value
    if not pasta.exists():
        return None

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
