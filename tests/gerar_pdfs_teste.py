import logging
from pathlib import Path

import playwright

from automation.src.application.services.branding_service import find_logo
from automation.src.config import settings
from automation.src.domain.models import Enterprise
from automation.src.infrastructure.browser.factory import (
    create_browser,
    create_context,
)
from automation.src.infrastructure.pdf.generator import generate_contract_html

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("teste_logo")

# ── DADOS MOCKADOS (simula o que viria do Triata) ──
DADOS_BASE: dict[str, str] = {
    "solicitante_empresa": "EMPRESA TESTE LTDA",
    "endereco_formatado": "Rua Exemplo, 123 - Centro",
    "cep_prestador": "03315-000",
    "cidade_estado": "São Paulo/SP",
    "cnpj_candidato": "00.000.000/0001-00",
    "nome_completo": "Maria da Silva",
    "estado_civil": "casada",
    "data_nascimento": "01/01/1990",
    "rg_candidato": "00.000.000-0",
    "cpf_candidato": "000.000.000-00",
    "qual_banco": "Banco do Brasil",
    "agencia_banco": "1234-5",
    "tipo_conta": "Corrente",
    "conta_banco": "12345-6",
    "titularidade_banco": "Maria da Silva",
    "pix_banco": "000.000.000-00",
    "data_atual": "15/06/2026",
    "valor_remuneracao": "R$ 5.000,00",
}


def gerar_pdf_para_empresa(
    empresa: Enterprise,
    empresa_form_field: str,
    output_name: str,
    context,
) -> Path:
    logo_path = find_logo(empresa)
    dados = dict(DADOS_BASE)
    dados["empresa_novo_calaborador"] = empresa_form_field  # p/ assinaturas

    output = settings.pdf_dir_path / output_name

    logger.info("Gerando %s com logo: %s", output_name, logo_path)

    resultado = generate_contract_html(
        dados=dados,
        output_path=output,
        template_path=settings.template_contrato_html_path,
        context=context,
        logo_path=logo_path,
    )

    if resultado:
        logger.info("✅ PDF gerado: %s", resultado)
        return resultado
    else:
        logger.error("❌ Falha ao gerar PDF para %s", empresa.value)
        raise RuntimeError(f"Falha ao gerar PDF para {empresa.value}")


def main():
    print("=" * 60)
    print("  TESTE DE LOGOS NO CONTRATO")
    print("  Gera 3 PDFs lado a lado para comparação visual")
    print("=" * 60)

    browser, playwright = create_browser(headless=True)
    context = create_context(browser)

    try:
        gerar_pdf_para_empresa(
            empresa=Enterprise.ARANTES,
            empresa_form_field="Arantes Arimura Advocacia",
            output_name="TESTE_Arantes.pdf",
            context=context,
        )

        gerar_pdf_para_empresa(
            empresa=Enterprise.GENTER,
            empresa_form_field="Genter Serviços em Recursos Humanos",
            output_name="TESTE_Genter.pdf",
            context=context,
        )

        gerar_pdf_para_empresa(
            empresa=Enterprise.FOLHA_TECH,
            empresa_form_field="Folha Tech Tecnologia",
            output_name="TESTE_FolhaTech.pdf",
            context=context,
        )

        print("\n" + "=" * 60)
        print("  ✅ 3 PDFs gerados em pdfs_gerados/")
        print("  Abra-os e compare as logos e footers nos PDFs!")
        print("=" * 60)

    finally:
        context.close()
        browser.close()
        playwright.stop()
        logger.info("Navegador fechado.")


if __name__ == "__main__":
    main()
