import base64
from pathlib import Path

from automation.src.infrastructure.pdf.generator import _build_logo_html


def _b64_of_file(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def test_logo_build_html_image_empresa():
    logos_dir = Path("logos")

    logo_arantes = logos_dir / "arantes" / "logo-v2.png"
    html_arantes = _build_logo_html(logo_arantes)
    assert 'src="data:image/png;base64,' in html_arantes
    assert _b64_of_file(logo_arantes) in html_arantes

    logo_genter = logos_dir / "genter" / "logo-v2.png"
    html_genter = _build_logo_html(logo_genter)
    assert 'src="data:image/png;base64,' in html_genter
    assert _b64_of_file(logo_genter) in html_genter

    logo_folhatech = logos_dir / "folhaTech" / "logo-v2.png"
    html_folhatech = _build_logo_html(logo_folhatech)
    assert 'src="data:image/png;base64,' in html_folhatech
    assert _b64_of_file(logo_folhatech) in html_folhatech

    assert html_arantes != html_genter, "Logo Arantes e Genter devem ser diferentes!"
    assert (
        html_genter != html_folhatech
    ), "Logo Genter e FolhaTech devem ser diferentes!"
    assert (
        html_arantes != html_folhatech
    ), "Logo Arantes e FolhaTech devem ser diferentes!"


def test_build_logo_html_sem_logo_retorna_fallback():
    html_sem_logo = _build_logo_html(None)
    assert "ARANTES ARIMURA" in html_sem_logo
    assert "ADVOCACIA" in html_sem_logo
    assert "base64" not in html_sem_logo, "Não deve conter imagem se não houver logo"
