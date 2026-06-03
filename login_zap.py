import os
import time
import json
import logging
import unicodedata
import re
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from difflib import SequenceMatcher

URL_LOGIN = "https://app.zapsign.com.br/acesso/entrar"

JSON_FILE = "dados_formulario_atual.json"
PDFS_GERADOS_DIR = "pdfs_gerados"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def screenshot_debug(page, filename: str):
    try:
        page.screenshot(path=filename, full_page=True)
        logging.info(f"📸 Screenshot: {filename}")
    except Exception:
        pass


def _normalize_text(s: str) -> str:
    if s is None:
        return ""

    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^\w\s-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    return s


def fechar_modal_se_existir(page, timeout_ms: int = 2500) -> bool:
    try:
        botao = page.locator("button[aria-label='Fechar modal']").first
        botao.wait_for(state="visible", timeout=timeout_ms)

        logging.info("⚠️ Modal detectado. Tentando fechar...")

        try:
            botao.click(timeout=1500)
        except Exception:
            pass

        try:
            if botao.is_visible():
                botao.click(force=True, timeout=1500)
        except Exception:
            pass

        try:
            if botao.is_visible():
                botao.dispatch_event("click")
        except Exception:
            pass

        try:
            handle = botao.element_handle()
            if handle:
                page.evaluate("(el) => el.click()", handle)
        except Exception:
            pass

        page.wait_for_timeout(700)

        try:
            ainda_visivel = False

            try:
                ainda_visivel = botao.is_visible()
            except Exception:
                ainda_visivel = False

            if ainda_visivel:
                logging.info("⚠️ Modal ainda visível. Removendo via JavaScript...")
                page.evaluate("""
                    () => {
                        const btn = document.querySelector("button[aria-label='Fechar modal']");
                        if (btn) btn.click();

                        const modal = document.querySelector("div.modal-content");
                        if (modal) {
                            modal.style.display = "none";
                            modal.style.visibility = "hidden";
                            modal.style.opacity = "0";
                            modal.remove();
                        }

                        document.querySelectorAll(
                            ".cdk-overlay-backdrop, .modal-backdrop, .overlay, .backdrop"
                        ).forEach(el => {
                            el.style.display = "none";
                            el.style.visibility = "hidden";
                            el.style.opacity = "0";
                            el.remove();
                        });
                    }
                """)

                page.wait_for_timeout(500)

        except Exception:
            pass

        logging.info("✅ Modal tratado.")
        return True

    except Exception:
        return False


def ler_json_carta_proposta() -> dict:
    base_dir = Path(__file__).resolve().parent
    json_path = base_dir / JSON_FILE

    if not json_path.exists():
        raise RuntimeError(f"JSON não encontrado: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nome = data.get("nome_completo")
    email = data.get("email_pessoal_candidato")

    if not nome:
        raise RuntimeError("Não encontrei 'nome_completo' no JSON.")

    return {
        "nome_cliente": str(nome).strip(),
        "email_cliente": str(email).strip() if email else None,
        "json_path": json_path.name,
        "json_full_path": json_path
    }


def encontrar_pdf_carta_proposta(nome_cliente: str) -> str:
    base_dir = Path(__file__).resolve().parent
    pasta_pdfs = base_dir / PDFS_GERADOS_DIR

    if not pasta_pdfs.exists():
        raise RuntimeError(f"Pasta não encontrada: {pasta_pdfs}")

    pdfs = [
        p for p in pasta_pdfs.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf"
    ]

    if not pdfs:
        raise RuntimeError(f"Nenhum PDF encontrado em: {pasta_pdfs}")

    nome_normalizado = _normalize_text(nome_cliente)

    candidatos = []

    for pdf in pdfs:
        nome_pdf = _normalize_text(pdf.stem)

        if nome_normalizado in nome_pdf or nome_pdf in nome_normalizado:
            candidatos.append(pdf)

    if candidatos:
        candidatos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return str(candidatos[0])

    pdf_mais_recente = max(pdfs, key=lambda p: p.stat().st_mtime)

    logging.warning(
        f"⚠️ Não encontrei PDF pelo nome '{nome_cliente}'. "
        f"Usando o PDF mais recente: {pdf_mais_recente.name}"
    )

    return str(pdf_mais_recente)


def esperar_upload_concluir(page, timeout_ms=180000):
    page.wait_for_timeout(2000)
    fechar_modal_se_existir(page)

    for sel in [
        ".mat-progress-spinner",
        ".mat-spinner",
        ".loading",
        ".loader",
        "[aria-busy='true']"
    ]:
        try:
            page.locator(sel).first.wait_for(state="hidden", timeout=3000)
        except Exception:
            pass

    fechar_modal_se_existir(page)


def clicar_continuar(page, timeout_ms=180000):
    fechar_modal_se_existir(page)

    btn = page.locator('[data-cy="continuarBtn"]')
    btn.wait_for(state="visible", timeout=timeout_ms)
    btn.scroll_into_view_if_needed()

    try:
        page.keyboard.press("Escape")
    except Exception:
        pass

    deadline = time.time() + (timeout_ms / 1000)

    while time.time() < deadline:
        try:
            fechar_modal_se_existir(page, timeout_ms=500)

            if btn.is_enabled():
                break

        except Exception:
            pass

        page.wait_for_timeout(300)

    else:
        screenshot_debug(page, "continuar_nao_habilitou.png")
        raise RuntimeError("Botão Continuar não habilitou.")

    for attempt in ("normal", "force", "js", "mouseevent"):
        try:
            fechar_modal_se_existir(page, timeout_ms=500)

            if attempt == "normal":
                btn.click(timeout=5000)
                return

            if attempt == "force":
                btn.click(force=True, timeout=5000)
                return

            if attempt == "js":
                page.evaluate("""
                    () => {
                        const el = document.querySelector('[data-cy="continuarBtn"]');
                        if (el) el.click();
                    }
                """)
                return

            if attempt == "mouseevent":
                page.evaluate("""
                    () => {
                        const el = document.querySelector('[data-cy="continuarBtn"]');
                        if (!el) return;

                        const rect = el.getBoundingClientRect();
                        const x = rect.left + rect.width / 2;
                        const y = rect.top + rect.height / 2;

                        ['mousemove', 'mousedown', 'mouseup', 'click'].forEach(type => {
                            el.dispatchEvent(new MouseEvent(type, {
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                clientX: x,
                                clientY: y
                            }));
                        });
                    }
                """)
                return

        except Exception:
            pass

    raise RuntimeError("Falha ao clicar no botão Continuar.")


def aplicar_visto_em_todas_as_paginas(page, timeout_ms=180000):
    fechar_modal_se_existir(page)

    logging.info("📄 Aguardando viewer do PDF carregar...")

    page.wait_for_selector("app-pdf-viewer .page[data-page-number]", timeout=timeout_ms)
    page.wait_for_selector("app-pdf-viewer .page[data-page-number] canvas", timeout=timeout_ms)

    paginas = page.locator("app-pdf-viewer .page[data-page-number]")
    total = paginas.count()

    if total == 0:
        raise RuntimeError("Não encontrei páginas no viewer do PDF.")

    logging.info(f"✅ Total de páginas encontradas: {total}")

    for i in range(total):
        fechar_modal_se_existir(page, timeout_ms=500)

        pagina = paginas.nth(i)
        num = pagina.get_attribute("data-page-number") or str(i + 1)

        pagina.scroll_into_view_if_needed()
        page.wait_for_timeout(200)

        canvas = pagina.locator("canvas").first
        canvas.wait_for(state="visible", timeout=timeout_ms)

        try:
            canvas.click(timeout=5000)
        except Exception:
            try:
                canvas.click(force=True, timeout=5000)
            except Exception:
                box = canvas.bounding_box()

                if not box:
                    raise RuntimeError(f"Não consegui bounding box do canvas na página {num}.")

                x = box["x"] + box["width"] / 2
                y = box["y"] + box["height"] / 2

                page.mouse.click(x, y, button="left")

        visto = page.locator("#zs-options-lines-visto")
        visto.wait_for(state="visible", timeout=30000)

        try:
            visto.click(timeout=5000)
        except Exception:
            try:
                visto.click(force=True, timeout=5000)
            except Exception:
                page.evaluate("""
                    () => {
                        const el = document.querySelector('#zs-options-lines-visto');
                        if (el) el.click();
                    }
                """)

        logging.info(f"✔️ Visto aplicado na página {num}")
        page.wait_for_timeout(250)


def esperar_pdf_viewer_renderizar(page, timeout_ms=90000):
    fechar_modal_se_existir(page)

    page.wait_for_selector(".pdfViewer", timeout=timeout_ms)
    page.wait_for_selector(".pdfViewer .page[data-page-number]", timeout=timeout_ms)
    page.wait_for_selector(".pdfViewer .page[data-page-number] canvas", timeout=timeout_ms)


def _scroll_viewer_to_bottom(page, viewer, max_steps=55):
    for _ in range(max_steps):
        try:
            last = viewer.locator(".page[data-page-number]").last
            last.scroll_into_view_if_needed()
        except Exception:
            pass

        page.wait_for_timeout(350)


def _click_canvas_center(page, canvas, label=""):
    canvas.wait_for(state="visible", timeout=30000)

    try:
        canvas.click(timeout=5000)
        return True

    except Exception:
        try:
            canvas.click(force=True, timeout=5000)
            return True

        except Exception:
            box = canvas.bounding_box()

            if not box:
                return False

            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2

            page.mouse.click(x, y, button="left")
            return True


def _click_assinatura_btn(page):
    fechar_modal_se_existir(page)

    assinatura = page.locator("#zs-options-lines-signature")
    assinatura.wait_for(state="visible", timeout=60000)
    assinatura.scroll_into_view_if_needed()

    try:
        assinatura.click(timeout=5000)
        return

    except Exception:
        try:
            assinatura.click(force=True, timeout=5000)
            return

        except Exception:
            page.evaluate("""
                () => {
                    const el = document.querySelector('#zs-options-lines-signature');
                    if (el) el.click();
                }
            """)


def assinar_ultima_pagina_todos_viewers(page, nome_alvo: str):
    esperar_pdf_viewer_renderizar(page, timeout_ms=90000)

    viewers = page.locator(".pdfViewer")
    total = viewers.count()

    if total == 0:
        logging.warning("⚠️ .pdfViewer não encontrado. Vou assinar usando páginas globais.")

        pages = page.locator(".page[data-page-number]")
        cnt = pages.count()

        if cnt == 0:
            raise RuntimeError("Não achei páginas para assinatura.")

        idxs = [cnt - 1, cnt - 2] if cnt >= 2 else [cnt - 1]

        for pidx in idxs:
            pg = pages.nth(pidx)
            canvas = pg.locator("canvas").first

            if _click_canvas_center(page, canvas, label="global"):
                _click_assinatura_btn(page)
                logging.info("✅ Assinatura selecionada no fallback global.")
                return

        return

    logging.info(f"📄 Total de contratos/viewers encontrados: {total}")

    for idx in range(total):
        fechar_modal_se_existir(page, timeout_ms=500)

        viewer = viewers.nth(idx)

        logging.info(f"📝 Processando viewer {idx + 1}/{total}")

        _scroll_viewer_to_bottom(page, viewer, max_steps=55)

        pages = viewer.locator(".page[data-page-number]")
        cnt = pages.count()

        if cnt == 0:
            logging.warning(f"⚠️ Viewer {idx + 1} sem páginas.")
            continue

        cand_idxs = [cnt - 1]

        if cnt >= 2:
            cand_idxs.append(cnt - 2)

        for pidx in cand_idxs:
            pg = pages.nth(pidx)
            canvas = pg.locator("canvas").first

            if _click_canvas_center(page, canvas, label=f"viewer_{idx + 1}"):
                _click_assinatura_btn(page)
                logging.info(f"✅ Assinatura selecionada no viewer {idx + 1}")
                break


def clicar_salvar_e_continuar(page, timeout_ms=120000):
    fechar_modal_se_existir(page)

    logging.info("➡️ Tentando clicar em 'Salvar e continuar'...")

    btn = page.locator("#save-and-continue-btn-test")
    btn.wait_for(state="visible", timeout=timeout_ms)
    btn.scroll_into_view_if_needed()

    deadline = time.time() + (timeout_ms / 1000)

    while time.time() < deadline:
        try:
            fechar_modal_se_existir(page, timeout_ms=500)

            if btn.is_enabled():
                break

        except Exception:
            pass

        page.wait_for_timeout(300)

    else:
        screenshot_debug(page, "salvar_continuar_nao_habilitou.png")
        raise RuntimeError("Botão 'Salvar e continuar' não habilitou.")

    for attempt in ("normal", "force", "js"):
        try:
            fechar_modal_se_existir(page, timeout_ms=500)

            if attempt == "normal":
                btn.click(timeout=5000)
                break

            elif attempt == "force":
                btn.click(force=True, timeout=5000)
                break

            elif attempt == "js":
                page.evaluate("""
                    () => {
                        const el = document.querySelector('#save-and-continue-btn-test');
                        if (el) el.click();
                    }
                """)
                break

        except Exception:
            continue

    logging.info("✅ Clique em 'Salvar e continuar' realizado.")
    page.wait_for_load_state("domcontentloaded")


def capturar_link_assinatura(page, timeout_ms=120000) -> str:
    fechar_modal_se_existir(page)

    logging.info("🔎 Aguardando campo de link da assinatura...")

    page.wait_for_function("""
        () => {
            const el = document.querySelector('input.signer_link');
            return el && el.value && el.value.startsWith('http');
        }
    """, timeout=timeout_ms)

    campo = page.locator("input.signer_link")
    link = campo.input_value()

    if not link.startswith("http"):
        raise RuntimeError("Link de assinatura inválido.")

    logging.info(f"🔗 Link capturado: {link}")
    return link


def salvar_link_no_json(json_path: Path, link: str):
    if not json_path.exists():
        raise RuntimeError(f"JSON não encontrado para salvar link: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "zapsign" not in data:
        data["zapsign"] = {}

    data["zapsign"]["link_assinatura"] = link
    data["zapsign"]["capturado_em"] = time.strftime("%Y-%m-%d %H:%M:%S")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    logging.info("💾 Link salvo no JSON com sucesso.")


def main():
    load_dotenv()

    email_login = os.getenv("ZAPSIGN_EMAIL")
    senha_login = os.getenv("ZAPSIGN_SENHA")

    if not email_login or not senha_login:
        raise RuntimeError("Defina ZAPSIGN_EMAIL e ZAPSIGN_SENHA no arquivo .env")

    base_dir = Path(__file__).resolve().parent

    logging.info("📥 Lendo JSON da carta proposta...")
    cliente = ler_json_carta_proposta()

    nome_cliente = cliente["nome_cliente"]
    email_cliente = cliente["email_cliente"]
    json_path = cliente["json_full_path"]

    logging.info(f"📄 JSON usado: {cliente['json_path']}")
    logging.info(f"👤 Candidato: {nome_cliente}")
    logging.info(f"📧 E-mail: {email_cliente}")

    pdf_carta = encontrar_pdf_carta_proposta(nome_cliente)
    arquivos_upload = [pdf_carta]

    logging.info("📎 PDF da carta proposta para assinatura:")
    logging.info(f"   - {pdf_carta}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=120)
        context = browser.new_context()
        page = context.new_page()

        try:
            # LOGIN - NOVO FLUXO: Email primeiro, depois Senha
            logging.info("🔐 Acessando login...")
            page.goto(URL_LOGIN, wait_until="domcontentloaded")
            fechar_modal_se_existir(page)

            # ETAPA 1: Preencher email e clicar em "Entrar"
            logging.info("📧 Etapa 1: Preenchendo email...")
            # Usa seletor por inputmode ou placeholder em vez de name
            campo_email = page.locator('input[inputmode="email"], input[placeholder*="e-mail"]').first
            campo_email.wait_for(state="visible", timeout=20000)
            campo_email.fill(email_login)
            logging.info("➡️ Clicando em 'Entrar' (Email)...")
            page.locator("button:has-text('Entrar')").first.click()

            # ETAPA 2: Aguardar campo de senha e preencher
            logging.info("⏳ Aguardando campo de senha...")
            campo_senha = page.locator('input[type="password"]')
            campo_senha.wait_for(state="visible", timeout=20000)
            campo_senha.fill(senha_login)
            logging.info("➡️ Clicando em 'Entrar' (Senha)...")
            page.locator("button:has-text('Entrar')").last.click()

            logging.info("⏳ Aguardando pós-login (#button-create-doc-sidebar-test)...")
            page.wait_for_selector("#button-create-doc-sidebar-test", timeout=40000)
            fechar_modal_se_existir(page)
            logging.info("✅ Login confirmado!")


            logging.info("📄 Criando documento...")
            btn_criar = page.locator("#button-create-doc-sidebar-test")
            btn_criar.scroll_into_view_if_needed()
            fechar_modal_se_existir(page)
            btn_criar.click()
            fechar_modal_se_existir(page)

            logging.info("⏳ Aguardando input de upload...")
            file_input = page.locator('input#files[type="file"]')
            file_input.wait_for(state="attached", timeout=30000)

            logging.info("⬆️ Enviando PDF gerado...")
            file_input.set_input_files(arquivos_upload)

            logging.info("⏳ Esperando processamento do upload...")
            esperar_upload_concluir(page, timeout_ms=180000)

            logging.info("➡️ Clicando em Continuar...")
            clicar_continuar(page, timeout_ms=180000)

            page.wait_for_load_state("domcontentloaded")
            fechar_modal_se_existir(page)

            logging.info("🔐 Ativando autenticação avançada...")

            toggle = page.locator("#toggle-authentication-test-id-input")
            toggle.wait_for(state="visible", timeout=30000)

            aria_checked = toggle.get_attribute("aria-checked")

            if aria_checked != "true":
                fechar_modal_se_existir(page)

                page.locator('label[for="toggle-authentication-test-id-input"]').click()
                page.wait_for_timeout(300)

                page.wait_for_function("""
                    () => document.querySelector('#toggle-authentication-test-id-input')
                        ?.getAttribute('aria-checked') === 'true'
                """, timeout=15000)

            logging.info("✅ Autenticação avançada ativada.")

            logging.info("✍️ Preenchendo nome do signatário...")

            campo_nome = page.locator("#signer-name-field-test-id")
            campo_nome.wait_for(state="visible", timeout=30000)
            campo_nome.click()
            campo_nome.fill(nome_cliente)

            page.wait_for_function("""
                () => {
                    const el = document.querySelector('#signer-name-field-test-id');
                    return el && el.value && el.value.trim().length > 0;
                }
            """, timeout=10000)

            if email_cliente:
                logging.info("📧 Preenchendo e-mail do signatário...")

                campo_email_signer = page.locator("#signer-email-field-test-id")
                campo_email_signer.wait_for(state="visible", timeout=30000)
                campo_email_signer.click()
                campo_email_signer.fill(email_cliente)

                page.wait_for_function("""
                    () => {
                        const el = document.querySelector('#signer-email-field-test-id');
                        return el && el.value && el.value.includes('@');
                    }
                """, timeout=10000)

            logging.info("✅ Nome/e-mail preenchidos.")

            logging.info("➡️ Clicando no botão final Continuar...")

            btn_enviar = page.locator("#send-document-button-test")
            btn_enviar.wait_for(state="visible", timeout=60000)
            btn_enviar.scroll_into_view_if_needed()

            deadline = time.time() + 60

            while time.time() < deadline:
                try:
                    fechar_modal_se_existir(page, timeout_ms=500)

                    if btn_enviar.is_enabled():
                        break

                except Exception:
                    pass

                page.wait_for_timeout(300)

            else:
                screenshot_debug(page, "botao_final_nao_habilitou.png")
                raise RuntimeError("Botão final não habilitou.")

            try:
                btn_enviar.click(timeout=5000)
            except Exception:
                try:
                    btn_enviar.click(force=True, timeout=5000)
                except Exception:
                    page.evaluate("""
                        () => {
                            const el = document.querySelector('#send-document-button-test');
                            if (el) el.click();
                        }
                    """)

            logging.info("✅ Clique final realizado.")
            page.wait_for_load_state("domcontentloaded")
            fechar_modal_se_existir(page)

            logging.info("📌 Aplicando visto em todas as páginas...")
            aplicar_visto_em_todas_as_paginas(page, timeout_ms=180000)

            logging.info("✍️ Inserindo campo de assinatura...")
            assinar_ultima_pagina_todos_viewers(page, nome_alvo=nome_cliente)

            logging.info("💾 Salvando e continuando...")
            clicar_salvar_e_continuar(page)

            link_assinatura = capturar_link_assinatura(page)

            salvar_link_no_json(
                json_path=json_path,
                link=link_assinatura
            )

            page.wait_for_timeout(4000)

        except PlaywrightTimeoutError as e:
            screenshot_debug(page, "debug_timeout.png")
            logging.error(f"❌ Timeout: {e}")

        except Exception as e:
            screenshot_debug(page, "debug_erro.png")
            logging.error(f"❌ Erro: {e}")

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()