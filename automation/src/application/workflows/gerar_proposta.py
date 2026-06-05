import logging

from automation.src.application.services.proposta_service import build_proposal
from automation.src.config import settings
from automation.src.domain.validators import clean_filename
from automation.src.infrastructure.browser.factory import create_page
from automation.src.infrastructure.external_apis.triata_client import TriataClient
from automation.src.infrastructure.pdf.generator import (
    generate_proposal_pdf,
    generate_contract_pdf,
)
from automation.src.infrastructure.storage import save, append_excel

logger = logging.getLogger("automacao.workflow.gerar_proposta")


def executar() -> str | None:
    """Executa o fluxo completo de geração de proposta.

    Returns:
        Caminho do PDF gerado, ou None se falhar.
    """
    page = create_page()

    try:
        client = TriataClient(
            page=page,
            url=settings.TRIATA_URL,
            username=settings.TRIATA_USERNAME,
            password=settings.TRIATA_PASSWORD,
        )
        dados = client.run()

        if not dados:
            logger.error("Falha ao extrair dados do Triata.")
            return None

        save(settings.json_path, dados)
        append_excel(settings.excel_path, dados)
        logger.info("Dados salvos em JSON e Excel.")

        proposta = build_proposal(dados)

        nome_arquivo = clean_filename(proposta.candidato.nome_completo)
        tarefa = proposta.tarefa_nome or ""

        if "04.1" in tarefa:
            output = settings.pdf_dir_path / f"Carta_Proposta_{nome_arquivo}.pdf"
            generate_proposal_pdf(proposta, output)
            logger.info("PDF da carta proposta gerado: %s", output)
        elif "08" in tarefa:
            output = settings.pdf_dir_path / f"Contrato_{nome_arquivo}.pdf"
            resultado = generate_contract_pdf(
                dados=dados,
                output_path=output,
                template_path=settings.template_contrato_path,
            )
            if resultado:
                logger.info("PDF do contrato gerado: %s", output)
            else:
                logger.error(
                    "Template de contrato não encontrado: %s",
                    settings.template_contrato_path,
                )
                return None
        else:
            logger.info("Tarefa '%s' não requer geração de PDF.", tarefa)
            return None

        return str(output)

    except Exception:
        logger.exception("Erro no fluxo de geração de proposta.")
        return None

    finally:
        page.context.browser.close()
        logger.info("Navegador fechado.")
