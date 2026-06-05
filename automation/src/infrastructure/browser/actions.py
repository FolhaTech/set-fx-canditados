import logging
import time

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from automation.src.domain.exceptions import ClickFailedError

logger = logging.getLogger("automacao.browser")


# Screenshot

def screenshot(page: Page, filename: str, full_page: bool = True) -> None:
    try:
        page.screenshot(path=filename, full_page=full_page)
        logger.info(f"Screenshot: {filename}")
    except Exception:
        pass


# Modal

def close_modal(page: Page, timeout_ms: int = 2500) -> bool:
    try:
        botao = page.locator("button[aria-label='Fechar modal']").first
        botao.wait_for(state="visible", timeout=timeout_ms)
        logger.info("Modal detectado. Fechando...")

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

        # Se ainda visível, remove via DOM
        try:
            if botao.is_visible():
                logger.info("Modal persistente. Removendo via JavaScript...")
                page.evaluate("""
                    () => {
                        const btn = document.querySelector(
                            "button[aria-label='Fechar modal']"
                        );
                        if (btn) btn.click();

                        const modal = document.querySelector("div.modal-content");
                        if (modal) {
                            modal.style.display = "none";
                            modal.style.visibility = "hidden";
                            modal.style.opacity = "0";
                            modal.remove();
                        }

                        document.querySelectorAll(
                            ".cdk-overlay-backdrop, .modal-backdrop, "
                            ".overlay, .backdrop"
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

        logger.info("Modal fechado.")
        return True

    except PlaywrightTimeoutError:
        return False
    except Exception:
        return False


# Click resilient

def safe_click(
        page: Page,
        selector: str,
        timeout_ms: int = 30_000,
        label: str = "",
) -> None:
    """Clica em um elemento com fallback progressivo.

    Estratégias: normal → force → JS evaluate → mouse event.

    Levanta ClickFailedError se todas falharem.

    Migrado do padrão repetido em:
      - clicar_continuar() em login_zap.py:234-281
      - clicar_salvar_e_continuar() em login_zap.py:513-532
      - _click_assinatura_btn() em login_zap.py:398-420
      - aplicar_visto_em_todas_as_paginas() em login_zap.py:335-346
      - main() em login_zap.py:755-766
    """
    label_str = f" ({label})" if label else ""

    close_modal(page, timeout_ms=500)

    btn = page.locator(selector).first
    btn.wait_for(state="visible", timeout=timeout_ms)
    btn.scroll_into_view_if_needed()

    try:
        page.keyboard.press("Escape")
    except Exception:
        pass

    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        try:
            close_modal(page, timeout_ms=500)
            if btn.is_enabled():
                break
        except Exception:
            pass
        page.wait_for_timeout(300)
    else:
        screenshot(page, f"botao_nao_habilitou{label_str}.png")
        raise ClickFailedError(f"Botão não habilitou: {selector}{label_str}")

    for attempt in ("normal", "force", "js", "mouseevent"):
        try:
            close_modal(page, timeout_ms=500)

            if attempt == "normal":
                btn.click(timeout=5000)
                return

            if attempt == "force":
                btn.click(force=True, timeout=5000)
                return

            if attempt == "js":
                escaped = selector.replace("'", "\\'")
                page.evaluate(f"""
                    () => {{
                        const el = document.querySelector('{escaped}');
                        if (el) el.click();
                    }}
                """)
                return

            if attempt == "mouseevent":
                escaped = selector.replace("'", "\\'")
                page.evaluate(f"""
                    () => {{
                        const el = document.querySelector('{escaped}');
                        if (!el) return;
                        const rect = el.getBoundingClientRect();
                        const x = rect.left + rect.width / 2;
                        const y = rect.top + rect.height / 2;
                        ['mousemove','mousedown','mouseup','click'].forEach(type => {{
                            el.dispatchEvent(new MouseEvent(type, {{
                                bubbles: true, cancelable: true,
                                view: window, clientX: x, clientY: y
                            }}));
                        }});
                    }}
                """)
                return

        except Exception:
            continue

    raise ClickFailedError(f"Falha ao clicar: {selector}{label_str}")


# fill

def safe_fill(
        page: Page,
        selector: str,
        value: str,
        timeout_ms: int = 30_000,
) -> None:
    close_modal(page, timeout_ms=500)
    campo = page.locator(selector).first
    campo.wait_for(state="visible", timeout=timeout_ms)
    campo.click()
    campo.fill(value)
    logger.debug(f"Preenchido: {selector}")


def wait_for_value(page: Page, selector: str, condition: str, timeout_ms: int = 10_000) -> None:
    escaped = selector.replace("'", "\\'")
    page.wait_for_function(
        f"""
        () => {{
            const el = document.querySelector('{escaped}');
            return el && el.value && ({condition});
        }}
        """,
        timeout=timeout_ms,
    )


#  Canvas / PDF Viewer

def click_canvas_center(page: Page, canvas: Locator, label: str = "") -> bool:
    canvas.wait_for(state="visible", timeout=30_000)

    try:
        canvas.click(timeout=5000)
        return True
    except Exception:
        pass

    try:
        canvas.click(force=True, timeout=5000)
        return True
    except Exception:
        pass

    box = canvas.bounding_box()
    if not box:
        logger.warning(f"Bounding box não encontrada para canvas{(' ' + label) if label else ''}")
        return False

    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2
    page.mouse.click(x, y, button="left")
    return True


def scroll_viewer_to_bottom(page: Page, viewer: Locator, max_steps: int = 55) -> None:
    for _ in range(max_steps):
        try:
            last = viewer.locator(".page[data-page-number]").last
            last.scroll_into_view_if_needed()
        except Exception:
            pass
        page.wait_for_timeout(350)


def wait_for_spinners(page: Page, timeout_ms: int = 3_000) -> None:
    page.wait_for_timeout(2000)
    close_modal(page)

    for sel in [
        ".mat-progress-spinner",
        ".mat-spinner",
        ".loading",
        ".loader",
        "[aria-busy='true']",
    ]:
        try:
            page.locator(sel).first.wait_for(state="hidden", timeout=timeout_ms)
        except Exception:
            pass

    close_modal(page)
