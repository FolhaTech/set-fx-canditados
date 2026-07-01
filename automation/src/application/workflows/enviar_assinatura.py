import logging

from automation.src.config import settings
from automation.src.domain.exceptions import MandatoryFieldError
from automation.src.domain.validators import normalize_text
from automation.src.infrastructure.browser.factory import create_page
from automation.src.infrastructure.external_apis.zapsign_client import ZapSignClient
from automation.src.infrastructure.storage import get_field, save_signature_link

logger = logging.getLogger("automacao.workflow.enviar_assinatura")


def _find_pdf(nome_candidato: str, pdf_dir):
    """Busca PDF por nome do candidato, com fallback para o mais recente.

    Migrado de: encontrar_pdf_carta_proposta() → login_zap.py:147-182
    """
    pdfs = [p for p in pdf_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]

    if not pdfs:
        return None

    nome_normalizado = normalize_text(nome_candidato)

    matches = []
    for pdf in pdfs:
        nome_pdf = normalize_text(pdf.stem)
        if nome_normalizado in nome_pdf or nome_pdf in nome_normalizado:
            matches.append(pdf)

    if matches:
        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return str(matches[0])

    pdf_mais_recente = max(pdfs, key=lambda p: p.stat().st_mtime)
    logger.warning(
        "PDF pelo nome '%s' não encontrado. Usando o mais recente: %s",
        nome_candidato,
        pdf_mais_recente.name,
    )
    return str(pdf_mais_recente)


def executar() -> str | None:
    """Executa o fluxo completo de envio para assinatura."""
    if not settings.ZAPSIGN_EMAIL or not settings.ZAPSIGN_PASSWORD:
        raise MandatoryFieldError(
            "ZAPSIGN_EMAIL e ZAPSIGN_PASSWORD devem estar definidos no .env"
        )

    nome = get_field(settings.json_path, "nome_completo", required=True)
    email = get_field(settings.json_path, "email_pessoal_candidato")
    logger.info("Candidato: %s | Email: %s", nome, email)

    pdf_path = _find_pdf(nome, settings.pdf_dir_path)
    if not pdf_path:
        logger.error("Nenhum PDF encontrado em: %s", settings.pdf_dir_path)
        return None

    logger.info("PDF para upload: %s", pdf_path)

    page, browser, playwright = create_page()
    try:
        client = ZapSignClient(
            page=page,
            url=settings.ZAPSIGN_URL,
            email=settings.ZAPSIGN_EMAIL,
            senha=settings.ZAPSIGN_PASSWORD,
        )
        link = client.run_full_workflow(
            nome=nome,
            email=email,
            pdf_paths=[pdf_path],
        )

        save_signature_link(settings.json_path, link)
        logger.info("Link de assinatura salvo no JSON.")
        return link

    except Exception:
        logger.exception("Erro no fluxo de envio para assinatura.")
        return None

    finally:
        try:
            page.context.browser.close()
            logger.info("Navegador fechado.")
        except Exception:
            pass
        playwright.stop()
