import logging

from automation.src.config import settings
from automation.src.infrastructure.browser.factory import create_page
from automation.src.infrastructure.external_apis.triata_finalizar_client import (
    TriataFinalizarClient,
)
from automation.src.infrastructure.storage import read_signature_link

logger = logging.getLogger("automacao.workflow.finalizar_proposta")


def executar(processo_id: str | None = None) -> bool:
    if processo_id:
        candidates = list(
            (settings.PROJECT_ROOT / "dados").glob(f"{processo_id}_*.json")
        )
        if not candidates:
            logger.error(
                "Candidato %s não encontrado em dados/. Rode 'proposta' primeiro.",
                processo_id,
            )
            return False
        json_path = candidates[0]
    else:
        json_path = settings.json_path

    link, nome = read_signature_link(json_path)
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
