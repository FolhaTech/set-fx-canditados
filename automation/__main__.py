import sys

from automation.src.application.workflows import enviar_assinatura, gerar_proposta
from automation.src.config import get_logger, setup_logging

setup_logging()
logger = get_logger("main")

if __name__ == "__main__":
    etapa = sys.argv[1] if len(sys.argv) > 1 else "proposta"

    if etapa == "proposta":
        logger.info("=== PIPELINE 1: Gerar Proposta ===")
        resultado = gerar_proposta()
        if resultado:
            logger.info("PDF gerado: %s", resultado)
        else:
            logger.error("Falha ao gerar proposta.")

    elif etapa == "assinatura":
        logger.info("=== PIPELINE 2: Enviar para Assinatura ===")
        resultado = enviar_assinatura()
        if resultado:
            logger.info("Link: %s", resultado)
        else:
            logger.error("Falha ao enviar para assinatura.")

    elif etapa == "completo":
        logger.info("=== PIPELINE COMPLETA ===")
        pdf = gerar_proposta()
        if pdf:
            logger.info("PDF gerado: %s", pdf)
            link = enviar_assinatura()
            if link:
                logger.info("Link: %s", link)
        else:
            logger.error("Falha na pipeline completa.")

    else:
        print("Uso: python -m automation [proposta|assinatura|completo]")
