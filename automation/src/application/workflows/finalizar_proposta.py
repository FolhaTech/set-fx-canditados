import logging

from automation.src.config import settings
from automation.src.infrastructure.browser.factory import create_page
from automation.src.infrastructure.external_apis.triata_finalizar_client import (
    TriataFinalizarClient,
)
from automation.src.infrastructure.storage import read_signature_link

logger = logging.getLogger("automacao.workflow.finalizar_proposta")


def executar() -> bool:
    """Finaliza a tarefa 04.1 - Confecção Proposta no Triata após ZapSign."""
    link, nome = read_signature_link(settings.json_path)
    logger.info("Candidato: %s", nome)
    logger.info("Link ZapSign: %s", link)

    page, browser, playwright = create_page()
    try:
        client = TriataFinalizarClient(
            page=page,
            url=settings.TRIATA_URL,
            username=settings.TRIATA_USERNAME,
            password=settings.TRIATA_PASSWORD,
        )
        return client.run(link=link, nome=nome)
    except Exception:
        logger.exception("Erro no fluxo de finalização.")
        return False
    finally:
        try:
            page.context.browser.close()
            logger.info("Navegador fechado.")
        except Exception:
            pass
        playwright.stop()
