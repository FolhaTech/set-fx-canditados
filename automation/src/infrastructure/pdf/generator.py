import base64
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from automation.src.application.services.branding_service import (
    find_logo,
    find_signature,
    get_theme,
    find_signature_by_role,
    find_all_signatures_for_company,
)
from automation.src.domain import Enterprise
from automation.src.domain.models import Proposal
from automation.src.domain.validators import clean_value, format_currency
from automation.src.infrastructure.pdf.styles import build_styles


def create_table(
    titulo: str,
    linhas: list[tuple[str, str]],
    pdf_styles: dict,
    tema: dict[str, str],
) -> list:
    cor_primaria = colors.HexColor(tema["primaria"])
    cor_secundaria = colors.HexColor(tema["secundaria"])
    cor_texto = colors.HexColor(tema["texto"])

    # Line filter
    linhas_validas = [
        [clean_value(campo), clean_value(valor)]
        for campo, valor in linhas
        if clean_value(valor)
    ]

    if not linhas_validas:
        return []

    elementos = [Paragraph(titulo, pdf_styles["TituloSecao"])]

    tabela = Table(
        [["Campo", "Informação"]] + linhas_validas,
        colWidths=[5.2 * cm, 10.2 * cm],
    )

    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), cor_primaria),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 1), (-1, -1), cor_texto),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, cor_secundaria]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elementos.append(tabela)
    elementos.append(Spacer(1, 0.25 * cm))
    return elementos


def create_bullet_list(
    titulo: str,
    itens: list[str],
    pdf_styles: dict,
) -> list:
    if not itens:
        return []

    elementos = [Paragraph(titulo, pdf_styles["TituloSecao"])]

    for item in itens:
        elementos.append(Paragraph(f"• {item}", pdf_styles["TextoCarta"]))

    elementos.append(Spacer(1, 0.15 * cm))
    return elementos


def generate_proposal_pdf(proposta: Proposal, output_path: Path) -> Path:
    nome = proposta.candidato.nome_completo or "Candidato"
    empresa = proposta.empresa
    tema = get_theme(empresa)
    pdf_styles = build_styles(tema, empresa.value)

    # Document config
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    story = []

    # Logo
    logo_path = find_logo(empresa)
    if logo_path:
        logo = Image(str(logo_path), width=5.2 * cm, height=2.0 * cm)
        logo.hAlign = "CENTER"
        story.append(logo)
        story.append(Spacer(1, 0.3 * cm))
    else:
        story.append(Paragraph(empresa.value, pdf_styles["LogoEmpresa"]))

    # Section and Header
    data_carta = datetime.now().strftime("%d/%m/%Y")
    story.append(Paragraph("", pdf_styles["SloganEmpresa"]))
    story.append(Paragraph(f"São Paulo, {data_carta}", pdf_styles["DataCarta"]))
    story.append(Paragraph(f"Prezado(a) <b>{nome}</b>,", pdf_styles["TextoCarta"]))
    story.append(
        Paragraph(
            "É com satisfação que enviamos para você a proposta de prestação de serviço "
            "para juntar-se ao nosso time. Certamente esta será uma ótima parceria.",
            pdf_styles["TextoCarta"],
        )
    )

    story.append(Spacer(1, 0.2 * cm))
    story.append(
        HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#DDDDDD"))
    )
    story.append(Spacer(1, 0.25 * cm))

    # Formatted time
    honorario_str = ""
    if proposta.honorario is not None:
        honorario_str = (
            f"R$ {proposta.honorario:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    # Tables
    story.extend(
        create_table(
            "Dados da proposta",
            [
                ("Processo", proposta.processo_id or ""),
                ("Tarefa", proposta.tarefa_nome or ""),
                ("Modelo", proposta.modelo_nome or ""),
                ("Empresa solicitante", proposta.empresa_solicitante),
                ("Tipo de vaga", proposta.tipo_vaga),
                ("Centro de custo", proposta.centro_custo),
                ("Funcionário substituído", proposta.funcionario_substituicao),
                ("Honorário", honorario_str),
            ],
            pdf_styles,
            tema,
        )
    )

    c = proposta.candidato
    story.extend(
        create_table(
            "Dados do candidato",
            [
                ("Nome completo", c.nome_completo),
                ("Data de nascimento", c.data_nascimento or ""),
                ("Estado civil", c.estado_civil or ""),
                ("RG", c.rg or ""),
                ("CPF", c.cpf or ""),
                ("E-mail pessoal", c.email or ""),
                ("Celular pessoal", c.celular or ""),
            ],
            pdf_styles,
            tema,
        )
    )

    story.extend(
        create_table(
            "Endereço residencial",
            [
                ("Endereço completo", c.endereco.full_address),
            ],
            pdf_styles,
            tema,
        )
    )

    # Lists
    story.extend(
        create_bullet_list(
            "Equipamentos e periféricos inclusos",
            proposta.equipamentos,
            pdf_styles,
        )
    )
    story.extend(
        create_bullet_list(
            "Sistemas e acessos inclusos",
            proposta.sistemas,
            pdf_styles,
        )
    )

    # Terms and Fees
    story.append(Paragraph("Condições da proposta", pdf_styles["TituloSecao"]))
    if honorario_str:
        story.append(
            Paragraph(
                f"• Honorários: <b>{honorario_str}</b>",
                pdf_styles["TextoCarta"],
            )
        )
    else:
        story.append(
            Paragraph(
                "• Honorários: R$ __________________________",
                pdf_styles["TextoCarta"],
            )
        )

    story.append(Spacer(1, 1.1 * cm))

    # Candidate signature
    story.append(Paragraph("Cliente e aceito:", pdf_styles["Assinatura"]))
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph(f"<b>{nome}</b>", pdf_styles["Assinatura"]))
    story.append(
        Paragraph(
            "__________________________________________",
            pdf_styles["Assinatura"],
        )
    )

    # Signature of the person responsible
    nome_resp = proposta.nome_responsavel
    if nome_resp:
        story.append(Paragraph("Cliente e aceito:", pdf_styles["Assinatura"]))
        story.append(Spacer(1, 0.2 * cm))

    story.append(Spacer(1, 0.7 * cm))

    # Signature for image
    caminho_ass = find_signature(empresa)
    if caminho_ass:
        img_ass = Image(str(caminho_ass), width=4.5 * cm, height=1.8 * cm)
        img_ass.hAlign = "LEFT"
        story.append(img_ass)

    story.append(Paragraph(f"<b>{nome_resp}</b>", pdf_styles["Assinatura"]))
    story.append(
        Paragraph(
            "__________________________________________",
            pdf_styles["Assinatura"],
        )
    )
    story.append(Paragraph("Atenciosamente,", pdf_styles["Assinatura"]))
    story.append(Paragraph(f"<b>{empresa.value}</b>", pdf_styles["Assinatura"]))

    # Footer
    story.append(Spacer(1, 0.6 * cm))
    story.append(
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DDDDDD"))
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            "Documento gerado automaticamente pela automação de Confecção de Carta Proposta.",
            pdf_styles["Rodape"],
        )
    )

    # Generate
    doc.build(story)
    return output_path


def generate_contract_pdf(
    dados: dict,
    output_path: Path,
    template_path: Path,
    logo_path: Path | None = None,
) -> Path | None:
    if not template_path.exists():
        return None

    with open(template_path, encoding="utf-8") as f:
        texto = f.read()

    # Replacement {{placeholders}}
    placeholders = re.findall(r"\{\{(.*?)\}\}", texto)
    for p in placeholders:
        chave = p.strip()
        valor = clean_value(dados.get(chave, ""))
        if "honorario" in chave.lower() or "valor" in chave.lower():
            valor = format_currency(valor)
        texto = texto.replace(f"{{{{{p}}}}}", valor)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        margin=(2 * cm, 2 * cm, 2 * cm, 2 * cm),
    )

    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    styles = getSampleStyleSheet()
    style_justificado = ParagraphStyle(
        name="Justificado",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
    )

    story = []

    if logo_path and logo_path.exists():
        story.append(Image(str(logo_path), width=5 * cm, height=1.8 * cm))
        story.append(Spacer(1, 1 * cm))

    for linha in texto.split("\n"):
        if linha.strip():
            story.append(Paragraph(linha.replace("\n", "<br/>"), style_justificado))
        else:
            story.append(Spacer(1, 0.3 * cm))

    doc.build(story)
    return output_path


def _inject_signature(html: str, placeholder: str, signature_path: Path) -> str:
    ext = signature_path.suffix.lower().lstrip(".")
    mime_map = {
        "svg": "image/svg+xml",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }
    mime = mime_map.get(ext, "image/svg+xml")

    with open(signature_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    img_tag = (
        f'<img src="data:{mime};base64,{b64}" '
        f'style="max-height:40px; max-width:180px;">'
    )

    return html.replace(placeholder, img_tag)


def generate_contract_html(
    dados: dict,
    output_path: Path,
    template_path: Path,
    context,
    logo_path: Path | None = None,
) -> Path | None:
    if not template_path.exists():
        return None

    with open(template_path, encoding="utf-8") as f:
        html = f.read()

    placeholders = re.findall(r"\{\{(.*?)\}\}", html)
    for p in placeholders:
        chave = p.strip()
        if chave == "LOGO" or chave.startswith("ASSINATURA_"):
            continue

        valor = clean_value(dados.get(chave, ""))

        if "honorario" in chave.lower() or "valor" in chave.lower():
            valor = format_currency(valor)
        html = html.replace(f"{{{{{p}}}}}", valor)

    logo_htm = _build_logo_html(logo_path)
    html = html.replace("{{LOGO}}", logo_htm)

    empresa = Enterprise.from_string(dados.get("empresa_novo_calaborador", ""))
    ass_contratante = find_signature_by_role(empresa, "contratante")
    if ass_contratante:
        html = _inject_signature(html, "{{ASSINATURA_CONTRATANTE}}", ass_contratante)

    todas_ass = find_all_signatures_for_company(empresa)
    testemunhas = [
        path for papel, path in todas_ass.items() if papel.startswith("testemunha")
    ]

    for i, caminho in enumerate(testemunhas[:2], start=1):
        placeholder = f"{{{{ASSINATURA_TESTEMUNHA_{i}}}}}"
        html = _inject_signature(html, placeholder, caminho)

    page = context.new_page()
    page.set_content(html, wait_until="networkidle")
    page.pdf(
        path=str(output_path),
        format="A4",
        print_background=True,
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
    )
    page.close()

    return output_path


def _build_logo_html(logo_path: Path | None) -> str:
    fallback = (
        '<div style="display:flex;align-items:center;gap:8px;justify-content:flex-end;">'
        '<div style="font-size:28pt;font-weight:bold;color:#8B7355;font-family:serif;line-height:1;">AAA</div>'
        "<div>"
        '<div style="font-size:16pt;font-weight:bold;letter-spacing:2px;font-family:Arial,sans-serif;">ARANTES ARIMURA</div>'
        '<div style="font-size:8pt;letter-spacing:4px;font-family:Arial,sans-serif;">ADVOCACIA</div>'
        "</div>"
        "</div>"
    )

    if not logo_path:
        return fallback

    if logo_path.is_dir():
        logo_file = None
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            encontrados = list(logo_path.glob(ext))
            if encontrados:
                logo_file = encontrados[0]
                break
        if not logo_file:
            return fallback
    elif logo_path.is_file():
        logo_file = logo_path
    else:
        return fallback

    ext = logo_file.suffix.lower().lstrip(".")
    mime_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    mime = mime_map.get(ext, "image/jpeg")

    with open(logo_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    data_url = f"data:{mime};base64,{b64}"

    return (
        f'<img src="{data_url}" '
        f'style="max-height:50px; max-width:200px; display:block; margin-left:auto;">'
    )
