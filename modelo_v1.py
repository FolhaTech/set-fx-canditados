import time
import json
import logging
from pathlib import Path
from datetime import datetime
import re
import pandas as pd

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    Image
)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

LOGIN_URL = "https://workflow.folhatech.com.br/triata/Sistema.php?area=Processo&m=1&mp=1"

USERNAME = "robo.cadastro"
PASSWORD = "Robo@aut2024"

JSON_FILE = Path("dados_formulario_atual.json")
EXCEL_FILE = Path("dados_formularios.xlsx")
PDF_DIR = Path("pdfs_gerados")
LOGOS_DIR = Path("Logos")

PDF_DIR.mkdir(exist_ok=True)
# Configurações
TEMPLATE_CONTRATO = Path("modelo_contrato.txt")
TEMPLATE_PADRAO = "Contrato padrão para o processo {{processo_id}} referente à tarefa {{nome_tarefa}}."


from pathlib import Path

ASSINATURAS_DIR = Path("assinatura")

def buscar_assinatura_empresa(empresa):
    mapeamento = {"Genter": "AssArimura.png", "Arantes": "AssRapha.png", "Folha Tech": "AssFernando.png"}
    nome_arquivo = mapeamento.get(empresa)
    if nome_arquivo:
        caminho = ASSINATURAS_DIR / nome_arquivo
        if caminho.exists(): return caminho
    return None
    
# LOG
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S"
)

log = logging.getLogger("automacao")


# ============================================================
# UTILITÁRIOS
# ============================================================

def limpar_nome_arquivo(nome):
    nome = re.sub(r'[\/:*?"<>|]', "_", str(nome or "").strip())
    return nome.replace(" ", "_") or "Candidato"

def salvar_dados_contrato(dados: dict, processo_id: str) -> None:
    """
    Salva os dados extraídos do formulário de contrato em um arquivo JSON.

    Args:
        dados (dict): Dicionário com os dados do formulário.
        processo_id (str): Identificador do processo (usado no nome do arquivo).
    """
    try:
        # Define o nome do arquivo usando pathlib para garantir portabilidade
        caminho_arquivo = Path(f"dados_contrato_{processo_id}.json")
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        print(f"[INFO] Dados do contrato salvos em: {caminho_arquivo}")
    except Exception as e:
        print(f"[ERRO] Falha ao salvar JSON do contrato: {e}")
def limpar_valor(valor):
    if valor is None or str(valor).strip() in ["- Selecione algo -", "None", "null"]: return ""
    return str(valor).strip()


def formatar_moeda(valor):
    valor = limpar_valor(valor)
    if not valor: return ""
    try:
        numero = float(valor.replace(".", "").replace(",", "."))
        return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return f"R$ {valor}"



def item_checado(valor):
    if not isinstance(valor, str):
        return False

    return valor.strip().lower().startswith("[x]")


def limpar_item_check(valor):
    if not isinstance(valor, str):
        return ""

    return (
        valor.replace("[x]", "")
        .replace("[X]", "")
        .replace("[ ]", "")
        .strip()
    )


def normalizar_nome_empresa(nome):
    nome = (nome or "").strip().lower()
    if "folha" in nome and "tech" in nome: return "Folha Tech"
    if "arantes" in nome or "aaa" in nome: return "Arantes"
    if "genter" in nome: return "Genter"
    return nome.title()


def obter_tema_empresa(nome_empresa):
    empresa = normalizar_nome_empresa(nome_empresa)
    temas = {
        "Folha Tech": {"primaria": "#F58220", "secundaria": "#FFE8D1", "texto": "#333333"},
        "Genter": {"primaria": "#9E2F2A", "secundaria": "#F6E3E2", "texto": "#333333"},
        "Arantes": {"primaria": "#1D4ED8", "secundaria": "#DBEAFE", "texto": "#333333"}
    }
    return temas.get(empresa, temas["Genter"])



def buscar_logo_empresa(nome_empresa):
    pasta = normalizar_nome_empresa(nome_empresa)
    caminho_pasta = LOGOS_DIR / pasta
    if not caminho_pasta.exists(): return None
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
        arquivos = list(caminho_pasta.glob(ext))
        if arquivos: return arquivos[0]
    return None

def criar_pdf_contrato(dados):
    """Gera o PDF do contrato preenchendo o template .txt com os dados do formulário."""
    nome = limpar_valor(dados.get("nome_completo")) or "Candidato"
    nome_arquivo = limpar_nome_arquivo(nome)
    output_pdf = PDF_DIR / f"Contrato_{nome_arquivo}.pdf"

    if not TEMPLATE_CONTRATO.exists():
        log.error(f"Template de contrato não encontrado em: {TEMPLATE_CONTRATO}")
        return None

    try:
        with open(TEMPLATE_CONTRATO, "r", encoding="utf-8") as f:
            texto = f.read()

        # Substituição dinâmica de placeholders {{campo}}
        placeholders = re.findall(r"\{\{(.*?)\}\}", texto)
        for p in placeholders:
            chave = p.strip()
            valor = limpar_valor(dados.get(chave, ""))
            if "honorario" in chave.lower() or "valor" in chave.lower():
                valor = formatar_moeda(valor)
            texto = texto.replace(f"{{{{{p}}}}}", valor)

        doc = SimpleDocTemplate(str(output_pdf), pagesize=A4, margin=(2*cm, 2*cm, 2*cm, 2*cm))
        styles = getSampleStyleSheet()
        style_justificado = ParagraphStyle(name="Justificado", parent=styles["Normal"], fontName="Helvetica", 
                                          fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=10)

        story = []
        empresa = normalizar_nome_empresa(dados.get("empresa_colaborador_novo") or dados.get("empresa_solicitante"))
        logo_path = buscar_logo_empresa(empresa)
        if logo_path:
            story.append(Image(str(logo_path), width=5*cm, height=1.8*cm))
            story.append(Spacer(1, 1*cm))

        for linha in texto.split("\n"):
            if linha.strip():
                story.append(Paragraph(linha.replace("\n", "<br/>"), style_justificado))
            else:
                story.append(Spacer(1, 0.3*cm))

        doc.build(story)
        log.info(f"PDF do Contrato gerado: {output_pdf}")
        return output_pdf
    except Exception as e:
        log.error(f"Erro ao gerar PDF do contrato: {e}")
        return None
# ============================================================
# ACESSO AO SITE
# ============================================================

def acessar_site(page):
    log.info("Acessando o site...")

    page.goto(
        LOGIN_URL,
        wait_until="domcontentloaded",
        timeout=40000
    )

    page.wait_for_load_state("networkidle", timeout=30000)
    log.info("Site carregado.")


def fazer_login(page):
    log.info("Preenchendo usuário...")

    page.wait_for_selector('input[name="login"]', timeout=20000)
    page.fill('input[name="login"]', USERNAME)

    log.info("Preenchendo senha...")

    page.wait_for_selector('input[name="senha"]', timeout=20000)
    page.fill('input[name="senha"]', PASSWORD)

    log.info("Clicando no botão de login...")

    page.wait_for_selector(".TriataFixUiIE7", timeout=20000)
    page.click(".TriataFixUiIE7")

    log.info("Aguardando login...")

    try:
        page.wait_for_selector(
            'input[name="login"]',
            state="hidden",
            timeout=30000
        )

        page.wait_for_load_state("networkidle", timeout=30000)

        log.info("Login realizado com sucesso.")
        log.info(f"URL atual: {page.url}")
        log.info(f"Título da página: {page.title()}")

        return True

    except PWTimeout:
        log.error("Login não confirmado. O campo de login ainda está visível.")
        page.screenshot(path="erro_login.png")
        return False


def ativar_modo_teste(page):
    try:
        log.info("Ativando Modo Teste...")

        page.wait_for_selector(
            "span.btn_ativa_modo_teste",
            timeout=20000
        )

        page.click("span.btn_ativa_modo_teste")
        page.wait_for_load_state("networkidle", timeout=30000)

        log.info("Modo Teste ativado com sucesso.")
        return True

    except Exception as e:
        log.error(f"Erro ao ativar Modo Teste: {e}")
        page.screenshot(path="erro_modo_teste.png")
        return False


log = logging.getLogger(__name__)

def clicar_tarefa_confecao(page):
    """
    Clica na primeira tarefa da listagem e identifica o tipo pelo atributo title.
    Retorna (nome_tarefa, processo_id) ou (None, None) em caso de erro.
    """
    try:
        log.info("Aguardando listagem de tarefas...")
        page.wait_for_selector('td[id^="tarefa_"]', timeout=20000)
    except Exception as e:
        log.warning(f"Erro ao aguardar listagem de tarefas: {e}")
        try:
            page.screenshot(path="erro_tarefa_lista.png")
        except:
            pass
        return (None, None)

    try:
        tds = page.locator('td[id^="tarefa_"]').all()
        log.info(f"Encontradas {len(tds)} tarefas na listagem.")
        if not tds:
            log.warning("Nenhuma tarefa encontrada na listagem.")
            try:
                page.screenshot(path="erro_tarefa_lista.png")
            except:
                pass
            return (None, None)

        # Pega a primeira tarefa
        primeiro_td = tds[0]
        titulo = primeiro_td.get_attribute("title")
        id_td = primeiro_td.get_attribute("id")

        if not titulo or not id_td:
            log.warning("Primeira tarefa sem title ou id.")
            try:
                page.screenshot(path="erro_tarefa_lista.png")
            except:
                pass
            return (None, None)

        # Identifica pelo title
        titulo_lower = titulo.strip().lower()
        if "04.1 - confecção proposta" in titulo_lower:
            nome_tarefa = "04.1 - Confecção Proposta"
        elif "08 - confecção e assinatura (contrato)" in titulo_lower:
            nome_tarefa = "08 - Confecção e assinatura (Contrato)"
        else:
            log.warning(f"Primeira tarefa não é de confecção. Título: '{titulo}'")
            try:
                page.screenshot(path="erro_tarefa_lista.png")
            except:
                pass
            return (None, None)

        # Extrai processo_id do id
        import re
        match = re.search(r"tarefa_(\d+)_\d+", id_td)
        if not match:
            log.warning(f"Não foi possível extrair processo_id do id: {id_td}")
            try:
                page.screenshot(path="erro_tarefa_lista.png")
            except:
                pass
            return (None, None)
        processo_id = match.group(1)

        log.info(f"Primeira tarefa identificada: '{titulo}' (processo_id={processo_id})")

        # Aceita dialogs automaticamente
        page.on("dialog", lambda dialog: dialog.accept())

        log.info("Clicando na primeira tarefa...")
        primeiro_td.click()

        try:
            page.wait_for_selector("#TriareProcessoForm", timeout=20000)
            log.info("Formulário #TriareProcessoForm carregado.")
        except Exception as e:
            log.warning(f"Erro ao aguardar #TriareProcessoForm: {e}")
            try:
                page.screenshot(path="erro_tarefa_form.png")
            except:
                pass
            return (None, None)

        return (nome_tarefa, processo_id)

    except Exception as e:
        log.warning(f"Erro inesperado em clicar_tarefa_confecao: {e}")
        try:
            page.screenshot(path="erro_tarefa_click.png")
        except:
            pass
        return (None, None)

# ============================================================
# EXTRAÇÃO DO FORMULÁRIO
# ============================================================

def extrair_formulario(page):
    log.info("Extraindo TODOS os campos do formulário dinamicamente...")
    page.wait_for_selector("#TriareProcessoForm", timeout=20000)
    
    dados = page.evaluate("""
        () => {
            const form = document.querySelector("#TriareProcessoForm");
            const data = {
                extraido_em: new Date().toLocaleString("pt-BR"),
                url: window.location.href
            };

            // Seleciona todos os inputs, selects e textareas
            const elements = form.querySelectorAll("input, select, textarea");

            elements.forEach(el => {
                // Usa o ID como chave prioritária, se não tiver, usa o Name
                const key = el.id || el.name;
                if (!key) return;

                if (el.type === 'checkbox' || el.type === 'radio') {
                    // Para checkboxes, armazena se está marcado ou o valor se estiver marcado
                    data[key] = el.checked ? (el.value || true) : false;
                } else if (el.tagName === 'SELECT') {
                    // Para selects, pega o texto da opção selecionada
                    data[key] = el.options[el.selectedIndex] ? el.options[el.selectedIndex].text.trim() : "";
                } else {
                    // Para texto, hidden, data, etc.
                    data[key] = el.value || "";
                }
            });

            return data;
        }
    """)
    log.info(f"Total de {len(dados)} campos extraídos.")
    return dados


# ============================================================
# SALVAR JSON E EXCEL
# ============================================================

def salvar_json(dados):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

    log.info(f"JSON atualizado: {JSON_FILE}")


def achatar_dados(dados):
    linha = {}

    for chave, valor in dados.items():
        if isinstance(valor, dict):
            for sub_chave, sub_valor in valor.items():
                linha[f"{chave}_{sub_chave}"] = sub_valor
        else:
            linha[chave] = valor

    return linha


def salvar_excel_acumulado(dados):
    nova_linha = achatar_dados(dados)
    novo_df = pd.DataFrame([nova_linha])

    if EXCEL_FILE.exists():
        df_antigo = pd.read_excel(EXCEL_FILE)
        df_final = pd.concat([df_antigo, novo_df], ignore_index=True)
    else:
        df_final = novo_df

    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        df_final.to_excel(writer, sheet_name="Dados", index=False)

    log.info(f"Excel atualizado: {EXCEL_FILE}")


# ============================================================
# PDF
# ============================================================

def obter_itens_checados(dados, grupo):
    itens = []

    valores = dados.get(grupo, {})

    if isinstance(valores, dict):
        for _, valor in valores.items():
            if item_checado(valor):
                itens.append(limpar_item_check(valor))

    return itens


def criar_tabela(titulo, linhas, styles, tema):
    elementos = []

    cor_primaria = colors.HexColor(tema["primaria"])
    cor_secundaria = colors.HexColor(tema["secundaria"])
    cor_texto = colors.HexColor(tema["texto"])

    linhas_validas = [
        [limpar_valor(campo), limpar_valor(valor)]
        for campo, valor in linhas
        if limpar_valor(valor)
    ]

    if not linhas_validas:
        return elementos

    elementos.append(Paragraph(titulo, styles["TituloSecao"]))

    tabela = Table(
        [["Campo", "Informação"]] + linhas_validas,
        colWidths=[5.2 * cm, 10.2 * cm]
    )

    tabela.setStyle(TableStyle([
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
    ]))

    elementos.append(tabela)
    elementos.append(Spacer(1, 0.25 * cm))

    return elementos


def criar_lista(titulo, itens, styles):
    elementos = []

    if not itens:
        return elementos

    elementos.append(Paragraph(titulo, styles["TituloSecao"]))

    for item in itens:
        elementos.append(Paragraph(f"• {item}", styles["TextoCarta"]))

    elementos.append(Spacer(1, 0.15 * cm))

    return elementos


def criar_pdf_carta_proposta(dados):
    # 1. Identificação Básica
    nome = limpar_valor(dados.get("nome_completo")) or "Candidato"
    nome_arquivo = limpar_nome_arquivo(nome)
    
    # 2. Definição da Empresa para o Layout (Prioridade: empresa_colaborador_novo)
    # Se empresa_colaborador_novo estiver preenchida, usa ela; caso contrário, usa empresa_solicitante
    empresa_layout = limpar_valor(dados.get("empresa_colaborador_novo")) or limpar_valor(dados.get("empresa_solicitante"))
    empresa_normalizada = normalizar_nome_empresa(empresa_layout)
    
    # 3. Definição de Tema e Cores
    tema = obter_tema_empresa(empresa_layout)
    cor_primaria = colors.HexColor(tema["primaria"])
    cor_texto = colors.HexColor(tema["texto"])
    
    # 4. Configuração do Documento
    output_pdf = PDF_DIR / f"Carta_Proposta_{nome_arquivo}.pdf"
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )
    
    # 5. Estilos
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="LogoEmpresa", parent=styles["Title"], fontName="Helvetica-Bold", 
        fontSize=30, textColor=cor_primaria, alignment=TA_CENTER, spaceAfter=0
    ))
    styles.add(ParagraphStyle(
        name="SloganEmpresa", parent=styles["Normal"], fontName="Helvetica", 
        fontSize=8, textColor=colors.HexColor("#777777"), alignment=TA_CENTER, spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        name="DataCarta", parent=styles["Normal"], fontName="Helvetica", 
        fontSize=10, textColor=cor_texto, alignment=TA_RIGHT, spaceAfter=22
    ))
    styles.add(ParagraphStyle(
        name="TextoCarta", parent=styles["Normal"], fontName="Helvetica", 
        fontSize=10, leading=15, textColor=cor_texto, alignment=TA_LEFT, spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name="TituloSecao", parent=styles["Heading2"], fontName="Helvetica-Bold", 
        fontSize=12, textColor=cor_primaria, spaceBefore=8, spaceAfter=7
    ))
    styles.add(ParagraphStyle(
        name="Assinatura", parent=styles["Normal"], fontName="Helvetica", 
        fontSize=10, textColor=cor_texto, alignment=TA_LEFT, spaceAfter=5
    ))
    styles.add(ParagraphStyle(
        name="Rodape", parent=styles["Normal"], fontName="Helvetica", 
        fontSize=8, textColor=colors.HexColor("#888888"), alignment=TA_RIGHT, leading=11
    ))

    # 6. Construção do Conteúdo (Story)
    story = []
    
    # Logo
    logo_path = buscar_logo_empresa(empresa_layout)
    if logo_path:
        logo = Image(str(logo_path), width=5.2 * cm, height=2.0 * cm)
        logo.hAlign = "CENTER"
        story.append(logo)
        story.append(Spacer(1, 0.3 * cm))
    else:
        story.append(Paragraph(empresa_normalizada or "Genter", styles["LogoEmpresa"]))
    
    # Cabeçalho e Saudação
    data_carta = datetime.now().strftime("%d/%m/%Y")
    story.append(Paragraph("", styles["SloganEmpresa"]))
    story.append(Paragraph(f"São Paulo, {data_carta}", styles["DataCarta"]))
    story.append(Paragraph(f"Prezado(a) <b>{nome}</b>,", styles["TextoCarta"]))
    story.append(Paragraph(
        "É com satisfação que enviamos para você a proposta de prestação de serviço "
        "para juntar-se ao nosso time. Certamente esta será uma ótima parceria.",
        styles["TextoCarta"]
    ))
    
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#DDDDDD")))
    story.append(Spacer(1, 0.25 * cm))

    # Dados Variáveis
    honorario = formatar_moeda(dados.get("honorario_novo_colaborador"))
    equipamentos = obter_itens_checados(dados, "equipamentos")
    sistemas = obter_itens_checados(dados, "sistemas")
    
    endereco_completo = " ".join([
        limpar_valor(dados.get("endereco_completo")),
        limpar_valor(dados.get("numero_endereco")),
        limpar_valor(dados.get("complemento_endereco")),
        limpar_valor(dados.get("bairro_prestador")),
        limpar_valor(dados.get("cidade_prestador")),
        limpar_valor(dados.get("cep_prestador")),
    ]).strip()

    # Tabelas de Informações
    story.extend(criar_tabela("Dados da proposta", [
        ("Processo", dados.get("processo_id")),
        ("Tarefa", dados.get("tarefa_nome")),
        ("Modelo", dados.get("modelo_nome")),
        ("Empresa solicitante", empresa_layout),
        ("Tipo de vaga", dados.get("tipo_vaga")),
        ("Empresa novo colaborador", dados.get("empresa_colaborador_novo")),
        ("Centro de custo", dados.get("centro_custo")),
        ("Funcionário substituído", dados.get("funcionario_substituicao")),
        ("Honorário", honorario),
    ], styles, tema))

    story.extend(criar_tabela("Dados do candidato", [
        ("Nome completo", dados.get("nome_completo")),
        ("Data de nascimento", dados.get("data_nascimento")),
        ("Estado civil", dados.get("estado_civil")),
        ("RG", dados.get("rg_candidato")),
        ("CPF", dados.get("cpf_candidato")),
        ("E-mail pessoal", dados.get("email_pessoal_candidato")),
        ("Celular pessoal", dados.get("celular_candidato")),
    ], styles, tema))

    story.extend(criar_tabela("Endereço residencial", [
        ("Endereço completo", endereco_completo),
    ], styles, tema))

    # Listas
    story.extend(criar_lista("Equipamentos e periféricos inclusos", equipamentos, styles))
    story.extend(criar_lista("Sistemas e acessos inclusos", sistemas, styles))

    # Condições e Assinaturas
    story.append(Paragraph("Condições da proposta", styles["TituloSecao"]))
    if honorario:
        story.append(Paragraph(f"• Honorários: <b>{honorario}</b>", styles["TextoCarta"]))
    else:
        story.append(Paragraph("• Honorários: R$ __________________________", styles["TextoCarta"]))

    story.append(Spacer(1, 1.1 * cm))
    
    # Bloco de Assinatura do Candidato e Responsável
    nome_resp = limpar_valor(dados.get("nome_responsavel_legal"))
    email_resp = limpar_valor(dados.get("email_responsavel_legal"))

   
    story.append(Paragraph("Cliente e aceito:", styles["Assinatura"]))
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph(f"<b>{nome}</b>", styles["Assinatura"]))
    story.append(Paragraph("__________________________________________", styles["Assinatura"]))
    
    # Inclusão do Responsável Legal se houver dados
    if nome_resp:
        
        story.append(Paragraph("Cliente e aceito:", styles["Assinatura"]))
        story.append(Spacer(1, 0.2 * cm))
        

        # Assinatura da Empresa
    story.append(Spacer(1, 0.7 * cm))
    
    
    
    # Busca e insere a imagem da assinatura
    caminho_ass = buscar_assinatura_empresa(empresa_normalizada)
    if caminho_ass:
        # O ReportLab precisa do caminho como string
        img_ass = Image(str(caminho_ass), width=4.5 * cm, height=1.8 * cm)
        img_ass.hAlign = 'LEFT'
        story.append(img_ass)
    story.append(Paragraph(f"<b>{nome_resp}</b>", styles["Assinatura"]))
    story.append(Paragraph("__________________________________________", styles["Assinatura"]))
    story.append(Paragraph("Atenciosamente,", styles["Assinatura"]))
    story.append(Paragraph(f"<b>{empresa_normalizada}</b>", styles["Assinatura"]))
    

    # Rodapé
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DDDDDD")))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "Documento gerado automaticamente pela automação de Confecção de Carta Proposta.",
        styles["Rodape"]
    ))

    # Gerar PDF
    doc.build(story)
    log.info(f"PDF criado com sucesso: {output_pdf}")
    return output_pdf
# ============================================================
# FLUXO DE SALVAMENTO
# ============================================================

def salvar_dados_formulario(page, nome_tarefa, processo_id=None):
    """
    Extrai dados do formulário e executa ação condicional.
    Adicionado argumento processo_id para precisão.
    """
    try:
        dados = extrair_formulario(page)
        if not dados:
            log.error("Falha ao extrair dados do formulário.")
            return False

        dados["tarefa_nome"] = nome_tarefa
        
        # Usa o processo_id vindo da listagem se disponível, senão tenta extrair
        if not processo_id:
            match = re.search(r"id=(\d+)", page.url) or re.search(r"processo=(\d+)", page.url)
            if match:
                processo_id = match.group(1)
        
        if processo_id:
            dados["processo_id"] = processo_id

        salvar_json(dados)
        salvar_excel_acumulado(dados)
        log.info("Dados salvos em JSON e Excel acumulado.")

        # Lógica de decisão de PDF baseada no nome da tarefa
        nome_tarefa_str = str(nome_tarefa).lower()
        
        if "04.1" in nome_tarefa_str:
            log.info("Gerando PDF da carta proposta...")
            criar_pdf_carta_proposta(dados)
        elif "08" in nome_tarefa_str:
            log.info("Identificada Tarefa 08. Gerando PDF do contrato...")
            criar_pdf_contrato(dados)
            salvar_dados_contrato(dados, processo_id)
        else:
            log.info(f"Tarefa '{nome_tarefa}' não requer geração de documento extra.")

        return True

    except Exception as e:
        log.error(f"Erro ao salvar dados do formulário: {e}")
        return False


# Configuração básica de log
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=50,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page = context.new_page()

        try:
            acessar_site(page)

            if fazer_login(page):
                # CORREÇÃO: clicar_tarefa_confecao retorna (nome_tarefa, processo_id)
                nome_tarefa, processo_id = clicar_tarefa_confecao(page)
                
                if nome_tarefa:
                    log.info(f"Tarefa identificada: {nome_tarefa}")
                    # Passa o nome_tarefa e o processo_id para a função de salvamento
                    if salvar_dados_formulario(page, nome_tarefa, processo_id):
                        log.info("Processo concluído com sucesso.")
                    else:
                        log.error("Falha ao processar dados do formulário.")
                else:
                    log.error("Nenhuma tarefa de confecção foi encontrada.")

        except Exception as e:
            log.exception(f"Erro inesperado: {e}")
            page.screenshot(path="erro_geral.png")

        finally:
            context.close()
            browser.close()
            log.info("Navegador fechado.")


if __name__ == "__main__":
    log.info("=" * 50)
    log.info("INICIANDO AUTOMAÇÃO")
    log.info("=" * 50)

    run()

    log.info("=" * 50)
    log.info("FINALIZADO")
    log.info("=" * 50)