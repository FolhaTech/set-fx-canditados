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
    PROSSEGUIR_SELECTOR = (
        "button[onclick*=\"TriareSubmeteProcesso('G', 'N', '0121000001301'\"]"
    )

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

        self.page.wait_for_selector(
            'input[name="login"]', state="hidden", timeout=30_000
        )
        self.page.wait_for_load_state("networkidle", timeout=30_000)
        logger.info("Login Triata confirmado.")

    def ativar_modo_teste(self) -> None:
        """Clica no botão Modo Teste e aceita o diálogo de confirmação."""
        logger.info("Ativando Modo Teste...")
        self.page.on("dialog", lambda dialog: dialog.accept())

        self.page.wait_for_timeout(5_000)

        clicado = False

        btn = self.page.locator(".btn_ativa_modo_teste")
        try:
            btn.wait_for(state="attached", timeout=10_000)
            btn.click()
            clicado = True
            logger.info("Modo Teste clicado na página principal.")
        except Exception:
            pass

        if not clicado:
            logger.info(
                "Botão não encontrado. Chamando ModoTeste('I') via JavaScript..."
            )
            try:
                self.page.evaluate("""
                    () => {
                        if (typeof ModoTeste === 'function') {
                            ModoTeste('I');
                        } else {
                            // Procurar o botão no DOM e clicar via JS
                            const btn = document.querySelector('.btn_ativa_modo_teste');
                            if (btn) btn.click();
                        }
                    }
                """)
                clicado = True
                logger.info("ModoTeste('I') chamado via JS.")
            except Exception as e:
                logger.warning("Falha ao ativar via JS: %s", e)

        if not clicado:
            logger.warning("Não foi possível ativar Modo Teste.")

        self.page.wait_for_load_state("networkidle", timeout=30_000)
        self.page.wait_for_timeout(3_000)
        self.page.wait_for_selector('td[id^="tarefa_"]', timeout=20_000)
        logger.info("Modo Teste processado.")

    def clicar_tarefa_confecao(self) -> bool:
        logger.info("Procurando tarefas")
        candidatos = [
            'td[title="04.1 - Confecção Proposta"]',
            'td[title="05.1 - Confecção Proposta"]',
            'td[title="08 - Confecção e assinatura (Contrato)"]',
        ]
        self.page.wait_for_timeout(2000)
        for selector in candidatos:
            elemento = self.page.query_selector(selector)
            if elemento:
                logger.info("Tarefa encontrada: %s", selector)
                elemento.scroll_into_view_if_needed()
                self.page.wait_for_timeout(500)
                try:
                    elemento.click(timeout=5_000)
                except Exception:
                    elemento.click(force=True, timeout=5_000)
                self.page.wait_for_load_state("networkidle", timeout=30_000)
                self.page.wait_for_selector("#TriareProcessoForm", timeout=30_000)
                return True

        raise TriataFinalizarError("Nenhuma tarefa encontrada na lista.")

    def preencher_consideracoes(
        self, link: str, texto: str = "concluido pelo robo"
    ) -> None:
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
            self.ativar_modo_teste()
            self.clicar_tarefa_confecao()
            self.preencher_consideracoes(link=link)
            self.clicar_prosseguir()
            return self.confirmar_prosseguimento()
        except TriataFinalizarError:
            raise
        except Exception:
            logger.exception("Erro inesperado no fluxo de finalização.")
            self.page.screenshot(
                path="erro_geral_finalizar_workflow.png", full_page=True
            )
            return False
