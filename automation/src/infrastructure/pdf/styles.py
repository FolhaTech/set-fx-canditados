from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def build_styles(theme: dict[str, str], enterprise_name: str) -> dict:
    primary_color = HexColor(theme["primaria"])
    text_color = HexColor(theme["texto"])

    styles = getSampleStyleSheet()

    # Enterprise title
    styles.add(ParagraphStyle(
        name="LogoEmpresa",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=30,
        textColor=primary_color,
        alignment=TA_CENTER,
        spaceAfter=0, ))

    # Slogan
    styles.add(ParagraphStyle(
        name="SloganEmpresa",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=HexColor("#777777"),
        alignment=TA_CENTER,
        spaceAfter=20,
    ))

    # Date and text
    styles.add(ParagraphStyle(
        name="DataCarta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=text_color,
        alignment=TA_RIGHT,
        spaceAfter=22,
    ))

    # Default text
    styles.add(ParagraphStyle(
        name="TextoCarta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=text_color,
        alignment=TA_LEFT,
        spaceAfter=8,
    ))

    # Section title
    styles.add(ParagraphStyle(
        name="TituloSecao",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=7,
    ))

    # Signature text
    styles.add(ParagraphStyle(
        name="Assinatura",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=text_color,
        alignment=TA_LEFT,
        spaceAfter=5,
    ))

    # Footer text
    styles.add(ParagraphStyle(
        name="Rodape",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=HexColor("#888888"),
        alignment=TA_RIGHT,
        leading=11,
    ))

    return styles
