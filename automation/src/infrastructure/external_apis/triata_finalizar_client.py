import logging

from playwright.sync_api import Page

from automation.src.domain.exceptions import TriataFinalizarError
from automation.src.infrastructure.browser.actions import (
    safe_click,
    safe_fill,
)

logger = logging.getLogger("automacao.triata.finalizar")


class TriataFinalizarClient:
    """Finaliza a tarefa 04.1 - Confecção Proposta no Triata após ZapSign."""

    PROSSEGUIR_JS = "TriareSubmeteProcesso('G', 'N', '0121000001301', ...arguments)"
    PROSSEGUIR_SELECTOR = "button[onclick*=\"TriareSubmeteProcesso('G', 'N', '0121000001301'\"]"

    def __init__(self, page: Page, url: str, username: str, password: str):
        self.page = page
        self.url = url
        self.username = username
        self.password = password

    def login(self) -> None:
        logger.info("Acessando Triata...")
        self.page.goto(self.url, wait_until="domcontentloaded", timeout=40_000)
        self.page.wait_for_load_state("networkidle", timeout=30_000)

        logger.info("Preenchendo usuário...")
        safe_fill(self.page, 'input[name="login"]', self.username)

        logger.info("Preenchendo senha...")
        safe_fill(self.page, 'input[name="senha"]', self.password)

        logger.info("Clicando no botão de login...")
        safe_click(self.page, ".TriataFixUiIE7", label="Login Triata")

        self.page.wait_for_selector('input[name="login"]', state="hidden", timeout=30_000)
        self.page.wait_for_load_state("networkidle", timeout=30_000)
        logger.info("Login Triata confirmado.")

    def aguardar_modo_teste_manual(self, timeout_ms: int = 120_000) -> None:

        logger.info(
            "Aguardando ativação manual do modo de teste (até %ds)...",
            timeout_ms // 1000,
        )
        self.page.wait_for_function(
            """
            () => {
                const el = document.querySelector('span.btn_ativa_modo_teste');
                if (!el) return true;
                const style = window.getComputedStyle(el);
                return style.display === 'none' || style.visibility === 'hidden';
            }
            """,
            timeout=timeout_ms,
        )
        logger.info("Modo de teste detectado como ativo.")

    def clicar_tarefa_confecao(self) -> bool:
        logger.info("Procurando tarefa: 04.1 - Confecção Proposta")
        seletor = 'td[title="04.1 - Confecção Proposta"]'
        self.page.wait_for_timeout(2000)
        elemento = self.page.query_selector(seletor)
        if not elemento:
            self.page.screenshot(path="tarefa_nao_encontrada.png", full_page=True)
            raise TriataFinalizarError("Tarefa 04.1 não encontrada na lista.")

        elemento.scroll_into_view_if_needed()
        self.page.wait_for_timeout(500)
        try:
            elemento.click(timeout=5000)
        except Exception:
            elemento.click(force=True, timeout=5000)

        self.page.wait_for_load_state("networkidle", timeout=30_000)
        self.page.wait_for_selector("#TriareProcessoForm", timeout=30_000)
        logger.info("Tarefa 04.1 aberta.")
        return True

    def preencher_consideracoes(self, link: str, texto: str = "concluido pelo robo") -> None:
        logger.info("Preenchendo #ass_prestador com o link...")
        self.page.wait_for_selector("#ass_prestador", timeout=20_000)
        self.page.evaluate(
            """
            (link) => {
                const campo = document.querySelector('#ass_prestador');
                if (!campo) throw new Error('#ass_prestador não encontrado');
                campo.value = link;
                campo.dispatchEvent(new Event('input', { bubbles: true }));
                campo.dispatchEvent(new Event('change', { bubbles: true }));
                if (typeof bTeveAlteracao !== 'undefined') bTeveAlteracao = true;
            }
            """,
            link,
        )

        logger.info("Preenchendo #consideracoes_historico...")
        self.page.wait_for_selector("#consideracoes_historico", timeout=20_000)
        self.page.evaluate(
            """
            (texto) => {
                const campo = document.querySelector('#consideracoes_historico');
                if (!campo) throw new Error('#consideracoes_historico não encontrado');
                campo.value = texto;
                campo.dispatchEvent(new Event('input', { bubbles: true }));
                campo.dispatchEvent(new Event('change', { bubbles: true }));
                if (typeof bTeveAlteracao !== 'undefined') bTeveAlteracao = true;
            }
            """,
            texto,
        )
        self.page.wait_for_timeout(500)
        logger.info("Campos preenchidos.")

    def clicar_prosseguir(self) -> bool:
        logger.info("Clicando em Prosseguir...")
        botao = self.page.locator(self.PROSSEGUIR_SELECTOR).first
        botao.wait_for(state="visible", timeout=20_000)
        botao.scroll_into_view_if_needed()
        self.page.wait_for_timeout(500)
        try:
            botao.click(timeout=5000)
        except Exception:
            try:
                botao.click(force=True, timeout=5000)
            except Exception:
                self.page.evaluate(
                    """
                    (sel) => {
                        const el = document.querySelector(sel);
                        if (el) el.click();
                    }
                    """,
                    self.PROSSEGUIR_SELECTOR,
                )
        self.page.wait_for_load_state("networkidle", timeout=30_000)
        logger.info("Botão Prosseguir clicado.")
        return True

    def confirmar_prosseguimento(self) -> bool:
        try:
            logger.info("Aguardando botão 'Sim'...")
            botao_sim = self.page.locator('button:has-text("Sim")').first
            botao_sim.wait_for(state="visible", timeout=20_000)
            botao_sim.scroll_into_view_if_needed()
            self.page.wait_for_timeout(500)
            try:
                botao_sim.click(timeout=5000)
            except Exception:
                botao_sim.click(force=True, timeout=5000)
            self.page.wait_for_load_state("networkidle", timeout=30_000)
            logger.info("Botão 'Sim' clicado com sucesso.")
            return True
        except Exception as e:
            logger.error("Erro ao clicar no botão Sim: %s", e)
            self.page.screenshot(path="erro_confirmacao_sim.png", full_page=True)
            return False

    def run(self, link: str, nome: str) -> bool:
        try:
            self.login()
            self.aguardar_modo_teste_manual()
            self.clicar_tarefa_confecao()
            self.preencher_consideracoes(link=link)
            self.clicar_prosseguir()
            return self.confirmar_prosseguimento()
        except TriataFinalizarError:
            raise
        except Exception:
            logger.exception("Erro inesperado no fluxo de finalização.")
            self.page.screenshot(path="erro_geral_finalizar_workflow.png", full_page=True)
            return False
