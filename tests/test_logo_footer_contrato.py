from automation.src.application.services.branding_service import get_contato
from automation.src.config import settings
from automation.src.domain.models import Enterprise
from automation.src.infrastructure.pdf.generator import _build_footer


def test_footer_html_muda_por_empresa():
    footers = {
        empresa: _build_footer(get_contato(empresa))
        for empresa in (
            Enterprise.ARANTES,
            Enterprise.GENTER,
            Enterprise.FOLHA_TECH,
        )
    }

    assert footers[Enterprise.ARANTES] != footers[Enterprise.GENTER]
    assert footers[Enterprise.GENTER] != footers[Enterprise.FOLHA_TECH]
    assert footers[Enterprise.ARANTES] != footers[Enterprise.FOLHA_TECH]


def test_template_nao_esconde_footer():
    html = settings.template_contrato_html_path.read_text(encoding="utf-8")

    assert "{{FOOTER}}" in html
    assert "display: none !important" not in html
