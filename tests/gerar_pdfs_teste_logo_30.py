import base64
import json
import logging
from pathlib import Path

from automation.src.application.services.branding_service import (
    _load_contatos_config,
    find_logo,
)
from automation.src.config import settings
from automation.src.domain.models import Enterprise
from automation.src.infrastructure.browser.factory import create_browser, create_context

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("teste_logo_30")


def _build_header_html_30(logo_path: Path, empresa: Enterprise) -> str:
    if not logo_path or not logo_path.exists():
        return _header_fallback(empresa)

    ext = logo_path.suffix.lower().lstrip(".")
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
    mime = mime_map.get(ext, "image/png")

    with open(logo_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    data_url = f"data:{mime};base64,{b64}"

    nome_empresa = {
        Enterprise.ARANTES: "Arantes Arimura",
        Enterprise.GENTER: "genter",
        Enterprise.FOLHA_TECH: "Folha Tech",
    }.get(empresa, empresa.value)

    tagline = {
        Enterprise.GENTER: "TUDO GIRA EM TORNO DAS </span>PESSOAS</span>",
        Enterprise.ARANTES: "<span>ADVOCACIA</span>",
        Enterprise.FOLHA_TECH: "<span>TECNOLOGIA</span>",
    }.get(empresa, "")

    return f"""
    <div class="logo-block">
      <div class="logo-icon">
        <img src="{data_url}" style="max-height:38px; max-width:140px;">
      </div>
      <div style="font-size: 10pt;line-height: 1.5;">{tagline}</div>
    </div>"""


def _header_fallback(empresa: Enterprise) -> str:
    nome = {
        Enterprise.ARANTES: "ARANTES ARIMURA",
        Enterprise.GENTER: "genter",
        Enterprise.FOLHA_TECH: "Folha Tech",
    }.get(empresa, empresa.value)
    return f"""<div class="logo-block">
      <div class="logo-name">{nome}</div>
    </div>"""


def _load_contato(empresa: Enterprise) -> dict[str, str]:
    config_path = settings.PROJECT_ROOT / "empresas.json"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("contatos", {}).get(empresa.value, {})


def gerar_pdf_30(empresa: Enterprise, output_name: str, context) -> Path:
    template_path = settings.PROJECT_ROOT / "modelo_contrato_30.html"
    html = template_path.read_text(encoding="utf-8")

    logo_path = find_logo(empresa)
    header_html = _build_header_html_30(logo_path, empresa)
    html = html.replace("{{LOGO_HEADER_30}}", header_html)

    contato = _load_contato(empresa)
    for campo, placeholder in (
        ("endereco_linha_1", "{{ENDERECO_LINHA_1}}"),
        ("endereco_linha_2", "{{ENDERECO_LINHA_2}}"),
        ("telefone", "{{TELEFONE}}"),
        ("site", "{{SITE}}"),
        ("email", "{{EMAIL}}"),
    ):
        html = html.replace(placeholder, contato.get(campo, ""))

    output = settings.pdf_dir_path / output_name
    logger.info("Gerando %s com logo: %s", output_name, logo_path)

    page = context.new_page()
    page.set_content(html, wait_until="networkidle")
    page.pdf(
        path=str(output),
        format="A4",
        print_background=True,
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
    )
    page.close()

    logger.info("✅ PDF gerado: %s", output)
    return output


def main():
    print("=" * 60)
    print("  TESTE DE LOGOS - modelo_contrato_30.html")
    print("  Gera 3 PDFs para comparação visual")
    print("=" * 60)

    browser = create_browser(headless=True)
    context = create_context(browser)

    try:
        gerar_pdf_30(Enterprise.ARANTES, "TESTE_LOGO_30_Arantes.pdf", context)
        gerar_pdf_30(Enterprise.GENTER, "TESTE_LOGO_30_Genter.pdf", context)
        gerar_pdf_30(Enterprise.FOLHA_TECH, "TESTE_LOGO_30_FolhaTech.pdf", context)

        print("\n" + "=" * 60)
        print("  ✅ 3 PDFs gerados em pdfs_gerados/")
        print("  Abra e compare os cabeçalhos das páginas!")
        print("=" * 60)
        print("\n  📁 Arquivos:")
        for f in sorted(settings.pdf_dir_path.glob("TESTE_LOGO_30_*.pdf")):
            print(f"     {f.name}  ({f.stat().st_size / 1024:.0f} KB)")
    finally:
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
