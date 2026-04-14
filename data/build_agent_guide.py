"""Genera el PDF: NYX-AGENT-GUIDE.pdf"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Preformatted, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

OUT = os.path.join(os.path.dirname(__file__), "NYX-AGENT-GUIDE.pdf")

# ── Colores ──────────────────────────────────────
DARK = HexColor("#1a1a2e")
ACCENT = HexColor("#e94560")
BLUE = HexColor("#0f3460")
LIGHT_BG = HexColor("#f0f0f5")
GREEN = HexColor("#16813d")
ORANGE = HexColor("#e07c24")
GRAY = HexColor("#666666")
WHITE = HexColor("#ffffff")

# ── Estilos ──────────────────────────────────────
styles = getSampleStyleSheet()

sTitle = ParagraphStyle("NyxTitle", parent=styles["Title"], fontSize=28,
    textColor=DARK, spaceAfter=6, leading=34, alignment=TA_CENTER)

sSubtitle = ParagraphStyle("NyxSub", parent=styles["Normal"], fontSize=13,
    textColor=GRAY, alignment=TA_CENTER, spaceAfter=20)

sH1 = ParagraphStyle("NyxH1", parent=styles["Heading1"], fontSize=18,
    textColor=ACCENT, spaceBefore=24, spaceAfter=10, leading=22)

sH2 = ParagraphStyle("NyxH2", parent=styles["Heading2"], fontSize=14,
    textColor=BLUE, spaceBefore=16, spaceAfter=6, leading=18)

sH3 = ParagraphStyle("NyxH3", parent=styles["Heading3"], fontSize=12,
    textColor=DARK, spaceBefore=10, spaceAfter=4, leading=15, fontName="Helvetica-Bold")

sBody = ParagraphStyle("NyxBody", parent=styles["Normal"], fontSize=10,
    textColor=DARK, spaceAfter=6, leading=14, alignment=TA_JUSTIFY)

sBullet = ParagraphStyle("NyxBullet", parent=sBody, leftIndent=16,
    bulletIndent=6, spaceAfter=3, bulletFontSize=10)

sCode = ParagraphStyle("NyxCode", fontName="Courier", fontSize=8.5,
    textColor=DARK, backColor=LIGHT_BG, leftIndent=12, rightIndent=12,
    spaceBefore=6, spaceAfter=6, leading=12, borderWidth=0.5,
    borderColor=HexColor("#cccccc"), borderPadding=6)

sNote = ParagraphStyle("NyxNote", parent=sBody, fontSize=9,
    textColor=BLUE, leftIndent=12, rightIndent=12, backColor=HexColor("#eef2ff"),
    borderWidth=0.5, borderColor=BLUE, borderPadding=8, spaceBefore=8, spaceAfter=8)

sSmall = ParagraphStyle("NyxSmall", parent=sBody, fontSize=8.5,
    textColor=GRAY, spaceAfter=2)

sCost = ParagraphStyle("NyxCost", parent=sBody, fontSize=10,
    textColor=GREEN, fontName="Helvetica-Bold")

# ── Helpers ──────────────────────────────────────
def h1(t): return Paragraph(t, sH1)
def h2(t): return Paragraph(t, sH2)
def h3(t): return Paragraph(t, sH3)
def p(t): return Paragraph(t, sBody)
def bullet(t): return Paragraph(t, sBullet, bulletText="\u2022")
def code_block(t): return Preformatted(t, sCode)
def note(t): return Paragraph(t, sNote)
def spacer(h=6): return Spacer(1, h)
def hr(): return HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10, spaceBefore=10)


def make_table(headers, rows, col_widths=None):
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# ── Contenido ────────────────────────────────────
def build():
    doc = SimpleDocTemplate(OUT, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)

    story = []

    # ── PORTADA ──────────────────────────────────
    story.append(spacer(60))
    story.append(Paragraph("NYX TERMINAL", sTitle))
    story.append(Paragraph("Guia de Implementacion del Agente IA", ParagraphStyle(
        "Sub2", parent=sSubtitle, fontSize=16, textColor=ACCENT)))
    story.append(spacer(10))
    story.append(Paragraph("Opcion A: Tool Use Nativo de Claude", sSubtitle))
    story.append(spacer(30))
    story.append(hr())
    story.append(spacer(10))
    story.append(Paragraph("Hackathon - Abril 2026", ParagraphStyle(
        "Date", parent=sSubtitle, fontSize=11)))
    story.append(spacer(6))
    story.append(Paragraph("Documento tecnico para implementacion paso a paso", sSubtitle))
    story.append(spacer(40))

    # Box de resumen
    summary_data = [
        ["Componente", "Detalle"],
        ["Modelo IA", "Claude Sonnet 4 (claude-sonnet-4-20250514)"],
        ["Data local", "8.19 MB, 67 archivos en info/"],
        ["Busqueda live", "Apify Starter ($29/mes)"],
        ["Budget por query", "Max USD $0.50"],
        ["Framework API", "FastAPI + uvicorn"],
    ]
    story.append(make_table(summary_data[0], summary_data[1:], col_widths=[120, 320]))

    story.append(PageBreak())

    # ── 1. ARQUITECTURA ──────────────────────────
    story.append(h1("1. Arquitectura del Agente"))
    story.append(p("El agente sigue un patron <b>\"Local First\"</b>: siempre busca en la data descargada (gratis e instantanea) antes de hacer consultas live que cuestan plata."))
    story.append(spacer(8))

    story.append(h2("Flujo de una consulta"))
    flow_data = [
        ["Paso", "Accion", "Costo"],
        ["1", "Usuario hace una pregunta", "---"],
        ["2", "Claude analiza y decide que tools usar", "~$0.01"],
        ["3", "Busca en data local (info/ 8MB)", "GRATIS"],
        ["4", "Si alcanza: sintetiza respuesta", "~$0.005"],
        ["5", "Si NO alcanza: busqueda live Apify", "$0.02-0.05"],
        ["6", "Claude sintetiza respuesta final", "~$0.005"],
    ]
    story.append(make_table(flow_data[0], flow_data[1:], col_widths=[40, 300, 100]))
    story.append(spacer(8))

    story.append(note("<b>Dato clave:</b> El 80% de las consultas se resuelven SOLO con data local. "
                      "Apify se usa unicamente para \"ultima hora\" o investigar algo que no esta en los datos descargados."))

    story.append(spacer(8))
    story.append(h2("Diagrama de flujo"))
    flow_text = """  Usuario pregunta
        |
        v
  Claude analiza la pregunta
        |
        |--- Busca en data local (5 tools, GRATIS)
        |       store.py -> signals.py -> classifier.py
        |
        |--- Data local alcanza? -----SI-----> Responde directo
        |
        |--- NO: necesita data fresca
        |       |
        |       v
        |   Budget check ($0.50 max, 2 calls max)
        |       |
        |       v
        |   Apify: RAG Web Browser / Twitter scraper
        |       |
        |       v
        |   Claude sintetiza todo
        |
        v
  Respuesta + metadata (tools usados, costo, tiempo)"""
    story.append(code_block(flow_text))

    story.append(PageBreak())

    # ── 2. TOOLS LOCALES ─────────────────────────
    story.append(h1("2. Tools Locales (Gratis)"))
    story.append(p("Estos tools acceden a la data descargada en <b>info/</b> (67 archivos, 8.19 MB). "
                   "Son instantaneos y no cuestan nada. Claude los usa SIEMPRE como primera opcion."))
    story.append(spacer(6))

    # Tool 1
    story.append(h3("consultar_datos"))
    story.append(p("Accede a datos economicos crudos. Categorias disponibles:"))
    tools_data = [
        ["Categoria", "Contenido", "Datos"],
        ["dolar", "7 tipos: blue, oficial, MEP, CCL, mayorista, cripto, tarjeta", "90 dias historial c/u"],
        ["bcra", "Reservas, BADLAR, TM20, base monetaria, circulacion, depositos", "30-60 dias c/u"],
        ["riesgo_pais", "Riesgo pais actual + historial", "90 dias"],
        ["inflacion", "Inflacion mensual", "24 meses"],
        ["series", "IPC Nucleo, EMAE, IPC Nacional, TC Nominal", "24 meses"],
    ]
    story.append(make_table(tools_data[0], tools_data[1:], col_widths=[70, 250, 120]))
    story.append(spacer(6))

    # Tool 2
    story.append(h3("consultar_senales"))
    story.append(p("Senales derivadas del cruce de multiples fuentes:"))
    signals_data = [
        ["Senal", "Calculo", "Uso"],
        ["brecha", "Blue vs Oficial en %", "Detectar presion cambiaria"],
        ["tasa_real", "BADLAR - Inflacion 12m", "Tasa negativa = huida al dolar"],
        ["reservas", "Tendencia 30d de reservas BCRA", "Capacidad de intervencion"],
        ["presion", "Indice compuesto 0-100", "Semaforo general del mercado"],
    ]
    story.append(make_table(signals_data[0], signals_data[1:], col_widths=[70, 200, 170]))
    story.append(spacer(6))

    # Tool 3
    story.append(h3("consultar_noticias"))
    story.append(p("336 noticias de multiples fuentes. Filtro por fuente o busqueda por texto."))
    news_data = [
        ["Fuente", "Items", "Tipo"],
        ["RSS Ambito, Cronista, El Economista (3)", "128", "Titulares + resumen"],
        ["Articles Infobae, La Nacion, iProfesional, Ambito", "135", "Articulos completos"],
        ["RAG Web Browser (15 temas)", "73", "Busquedas tematicas"],
    ]
    story.append(make_table(news_data[0], news_data[1:], col_widths=[230, 50, 160]))
    story.append(spacer(6))

    # Tool 4
    story.append(h3("consultar_eventos"))
    story.append(p("Noticias clasificadas automaticamente en eventos con tipo y urgencia (1-10):"))
    event_types = [
        ["Tipo", "Ejemplos", "Activos afectados"],
        ["sindical", "Paros, huelgas, paritarias", "logistica, consumo"],
        ["regulatorio", "Comunicaciones BCRA, decretos, cepo", "dolar, bonos, acciones bancarias"],
        ["economico", "Inflacion, tasas, reservas, devaluacion", "bonos soberanos, acciones, dolar"],
        ["politico", "Leyes, presupuesto, elecciones", "bonos soberanos, riesgo pais"],
        ["climatico", "Sequia, inundaciones, heladas", "agro, soja, exportaciones"],
    ]
    story.append(make_table(event_types[0], event_types[1:], col_widths=[70, 210, 160]))
    story.append(spacer(6))

    # Tool 5
    story.append(h3("consultar_social"))
    story.append(p("Datos de redes sociales descargados:"))
    social_data = [
        ["Red", "Contenido", "Volumen"],
        ["Twitter", "12 busquedas: bcra, dolar_blue, inflacion, milei_economia...", "7,414 tweets"],
        ["Reddit", "r/merval (hot + new) + r/argentina economia", "67 posts"],
        ["Google Trends", "15 terminos economicos AR", "3 batches"],
    ]
    story.append(make_table(social_data[0], social_data[1:], col_widths=[70, 270, 100]))

    story.append(PageBreak())

    # ── 3. TOOLS LIVE ────────────────────────────
    story.append(h1("3. Tools Live (Cuestan Plata)"))
    story.append(p("Solo se usan cuando la data local no alcanza. <b>Maximo 2 calls por consulta</b> y <b>$0.50 de budget</b>."))
    story.append(spacer(8))

    story.append(h3("busqueda_web"))
    story.append(p("Usa <b>apify/rag-web-browser</b> para buscar en la web en tiempo real."))
    story.append(bullet("Costo estimado: ~$0.02 por query"))
    story.append(bullet("Ideal para: noticias de ultima hora, verificar datos especificos"))
    story.append(bullet("Devuelve: titulo, URL, texto (hasta 1500 chars por resultado)"))
    story.append(bullet("Max resultados: 10"))
    story.append(spacer(6))

    story.append(h3("busqueda_twitter"))
    story.append(p("Usa <b>xtdata/twitter-x-scraper</b> para buscar tweets en tiempo real."))
    story.append(bullet("Costo estimado: ~$0.05 por busqueda"))
    story.append(bullet("Ideal para: sentimiento de mercado en tiempo real, reacciones a eventos"))
    story.append(bullet("Devuelve: texto, autor, likes, fecha"))
    story.append(bullet("Max tweets: 50"))
    story.append(spacer(8))

    story.append(h2("Budget Guard"))
    story.append(p("El agente tiene un sistema de control de costos integrado:"))
    budget_data = [
        ["Parametro", "Valor", "Proposito"],
        ["max_budget_per_query", "$0.50", "Limite de gasto en Apify por consulta"],
        ["max_live_calls", "2", "Maximo de busquedas live por consulta"],
        ["APIFY_COST_ESTIMATES", "dict", "Costo estimado por actor para control previo"],
    ]
    story.append(make_table(budget_data[0], budget_data[1:], col_widths=[140, 80, 220]))
    story.append(spacer(6))
    story.append(note("<b>Seguridad:</b> Antes de ejecutar un tool live, el agente verifica que el costo estimado "
                      "no exceda el budget restante. Si lo excede, devuelve un error y Claude busca alternativas locales."))

    story.append(PageBreak())

    # ── 4. IMPLEMENTACION ────────────────────────
    story.append(h1("4. Implementacion Paso a Paso"))

    story.append(h2("Paso 1: Instalar dependencias"))
    story.append(code_block("pip install anthropic apify-client httpx feedparser fastapi uvicorn python-dotenv"))

    story.append(h2("Paso 2: Configurar .env"))
    story.append(code_block("""# .env
ANTHROPIC_API_KEY=sk-ant-...
APIFY_TOKEN=apify_api_YOUR_TOKEN_HERE
DIARICAT_LIVE_URL=http://127.0.0.1:8766"""))

    story.append(h2("Paso 3: Estructura del agente"))
    story.append(p("El agente tiene 3 componentes principales:"))
    story.append(spacer(4))

    story.append(h3("A) System Prompt"))
    story.append(p("Le dice a Claude quien es, que datos tiene, y las REGLAS:"))
    story.append(bullet("SIEMPRE buscar local primero (gratis)"))
    story.append(bullet("SOLO usar tools live si la data local no alcanza"))
    story.append(bullet("MAXIMO 2 busquedas live por consulta"))
    story.append(bullet("Responder en espanol argentino, con datos concretos"))
    story.append(bullet("Citar numeros especificos, no generalidades"))
    story.append(spacer(6))

    story.append(h3("B) Tool Definitions"))
    story.append(p("Se definen 7 tools con sus schemas JSON para Claude:"))
    tool_list = [
        ["Tool", "Tipo", "Schema resumen"],
        ["consultar_datos", "LOCAL", "categoria (enum), detalle (str), dias (int)"],
        ["consultar_senales", "LOCAL", "senal (enum: todas/brecha/tasa_real/reservas/presion)"],
        ["consultar_noticias", "LOCAL", "fuente (str), buscar (str), limite (int)"],
        ["consultar_eventos", "LOCAL", "tipo (enum), min_urgencia (int), limite (int)"],
        ["consultar_social", "LOCAL", "red (enum), query (str), buscar (str), limite (int)"],
        ["busqueda_web", "LIVE $", "query (str), max_results (int)"],
        ["busqueda_twitter", "LIVE $", "terminos (array[str]), max_tweets (int)"],
    ]
    story.append(make_table(tool_list[0], tool_list[1:], col_widths=[110, 60, 270]))
    story.append(spacer(6))

    story.append(h3("C) Agent Loop"))
    story.append(p("El loop principal del agente:"))
    story.append(code_block("""# Pseudocodigo del agent loop
messages = [{"role": "user", "content": pregunta}]

for i in range(MAX_ITERATIONS):           # max 6
    response = claude.messages.create(
        model="claude-sonnet-4-20250514",
        system=SYSTEM_PROMPT,
        tools=LOCAL_TOOLS + LIVE_TOOLS,
        messages=messages,
    )

    if response.stop_reason == "end_turn":
        return response.text              # Respuesta final

    # Claude pidio tools
    for tool_call in response.tool_uses:
        result = execute_tool(tool_call)  # Local o Apify
        # Agregar resultado al historial
        messages.append(assistant_msg)
        messages.append(tool_result_msg)

    # Claude sigue razonando con los resultados..."""))

    story.append(PageBreak())

    # ── 5. COSTOS ────────────────────────────────
    story.append(h1("5. Costos Estimados"))

    story.append(h2("Claude API"))
    claude_costs = [
        ["Modelo", "Input", "Output", "Costo por query"],
        ["Sonnet 4 (recomendado)", "$3/M tokens", "$15/M tokens", "~$0.01-0.03"],
        ["Haiku 4.5 (economia)", "$0.80/M tokens", "$4/M tokens", "~$0.003-0.01"],
        ["Opus 4.6 (maximo)", "$15/M tokens", "$75/M tokens", "~$0.05-0.15"],
    ]
    story.append(make_table(claude_costs[0], claude_costs[1:], col_widths=[140, 80, 80, 140]))
    story.append(spacer(6))

    story.append(h2("Apify"))
    apify_costs = [
        ["Plan", "Precio", "Uso incluido", "Para Nyx"],
        ["Free", "$0", "Limitado", "Solo para testing"],
        ["Starter", "$29/mes", "~$0.96/dia", "Hackathon + demo"],
    ]
    story.append(make_table(apify_costs[0], apify_costs[1:], col_widths=[80, 80, 120, 160]))
    story.append(spacer(6))

    story.append(h2("Costo total por consulta"))
    total_costs = [
        ["Escenario", "Claude", "Apify", "Total"],
        ["Solo data local (80% de queries)", "$0.01-0.03", "$0.00", "$0.01-0.03"],
        ["Con 1 busqueda web", "$0.02-0.04", "$0.02", "$0.04-0.06"],
        ["Con 1 busqueda Twitter", "$0.02-0.04", "$0.05", "$0.07-0.09"],
        ["Con web + Twitter (max)", "$0.03-0.05", "$0.07", "$0.10-0.12"],
        ["Budget cap", "---", "---", "$0.50 (nunca se alcanza)"],
    ]
    story.append(make_table(total_costs[0], total_costs[1:], col_widths=[160, 80, 70, 130]))
    story.append(spacer(6))
    story.append(note("<b>Estimacion diaria:</b> Con 50 consultas/dia, el costo total seria ~$1-3 "
                      "(Claude) + ~$0.50-1.50 (Apify) = <b>$1.50-4.50/dia</b>."))

    story.append(PageBreak())

    # ── 6. EJEMPLO DE USO ────────────────────────
    story.append(h1("6. Ejemplo de Uso"))

    story.append(h2("Uso basico"))
    story.append(code_block("""import os
from dotenv import load_dotenv
from core.agent import NyxAgent

load_dotenv()

agent = NyxAgent(
    anthropic_key=os.getenv("ANTHROPIC_API_KEY"),
    apify_token=os.getenv("APIFY_TOKEN"),
    model="claude-sonnet-4-20250514",
    max_budget_per_query=0.50,
    max_live_calls=2,
)

# Consulta simple (se resuelve con data local)
result = agent.ask(
    "Que esta pasando con el dolar hoy?",
    verbose=True
)

print(result["respuesta"])
print(f"Tools usados: {len(result['tool_calls'])}")
print(f"Calls live: {result['live_calls']}")
print(f"Gastado Apify: ${result['apify_spent']}")
print(f"Tiempo: {result['elapsed_s']}s")"""))
    story.append(spacer(8))

    story.append(h2("Output esperado (verbose=True)"))
    story.append(code_block("""  > consultar_datos({"categoria": "dolar"})
  > consultar_senales({"senal": "brecha"})
  > consultar_noticias({"buscar": "dolar", "limite": 5})

El dolar blue esta en $1390 (compra $1375), practicamente
igualado con el oficial a $1395. La brecha cambiaria es de
apenas -0.36%, lo que indica una calma cambiaria inusual.

En las ultimas noticias, el BCRA aprovecho esta ventana
para flexibilizar el cepo (Com. A 8417)...

Tools usados: 3
Calls live: 0
Gastado Apify: $0.0
Tiempo: 4.2s"""))
    story.append(spacer(8))

    story.append(h2("Consulta que requiere busqueda live"))
    story.append(code_block("""result = agent.ask(
    "Que dijeron hoy los economistas sobre la baja de tasas del BCRA?",
    verbose=True
)

# Output:
#   > consultar_datos({"categoria": "bcra", "detalle": "tasa_badlar"})
#   > consultar_noticias({"buscar": "tasa bcra"})
#   $ busqueda_web({"query": "economistas baja tasas BCRA abril 2026"})
#       gastado: $0.02 / $0.50
#   > consultar_social({"red": "twitter", "query": "bcra"})"""))

    story.append(PageBreak())

    # ── 7. ENDPOINTS API ─────────────────────────
    story.append(h1("7. Endpoints API (FastAPI)"))
    story.append(p("Ya existe <b>api.py</b> con endpoints de data. Para el agente, agregar:"))
    story.append(spacer(6))

    story.append(h2("Endpoint del agente"))
    story.append(code_block("""# Agregar en api.py
from pydantic import BaseModel

class AgentQuery(BaseModel):
    question: str
    max_budget: float = 0.50
    verbose: bool = False

@app.post("/agent/ask")
async def agent_ask(q: AgentQuery):
    from core.agent import NyxAgent
    agent = NyxAgent(
        anthropic_key=os.getenv("ANTHROPIC_API_KEY"),
        apify_token=os.getenv("APIFY_TOKEN"),
        max_budget_per_query=q.max_budget,
    )
    return agent.ask(q.question, verbose=q.verbose)"""))
    story.append(spacer(8))

    story.append(h2("Endpoints existentes"))
    endpoints = [
        ["Metodo", "Endpoint", "Descripcion"],
        ["GET", "/dolar", "Todos los tipos de dolar actuales"],
        ["GET", "/dolar/blue", "Solo dolar blue"],
        ["GET", "/dolar/historial/{tipo}", "Historial 30d por tipo"],
        ["GET", "/bcra/{variable}", "Variable BCRA (reservas, tasa_badlar, etc)"],
        ["GET", "/reservas", "Reservas internacionales"],
        ["GET", "/riesgo-pais", "Riesgo pais actual"],
        ["GET", "/riesgo-pais/historial", "Historial riesgo pais"],
        ["GET", "/inflacion", "Inflacion mensual (12m)"],
        ["GET", "/signals", "Todas las senales derivadas"],
        ["GET", "/signals/brecha", "Brecha cambiaria"],
        ["GET", "/signals/tasa-real", "Tasa real (BADLAR vs inflacion)"],
        ["GET", "/signals/presion", "Indice de presion cambiaria"],
        ["GET", "/noticias", "Noticias (filtro por fuente)"],
        ["GET", "/eventos", "Eventos clasificados"],
        ["GET", "/tweets", "Tweets (filtro por query)"],
        ["GET", "/reddit", "Posts de Reddit"],
        ["GET", "/trends", "Google Trends AR"],
        ["POST", "/agent/ask", "Pregunta al agente IA (NUEVO)"],
    ]
    story.append(make_table(endpoints[0], endpoints[1:], col_widths=[45, 150, 245]))

    story.append(PageBreak())

    # ── 8. ESTRUCTURA ────────────────────────────
    story.append(h1("8. Estructura del Proyecto"))
    story.append(code_block("""Nyx Terminal/
|-- main.py                    # Entry point CLI (muestra resumen)
|-- api.py                     # FastAPI server (uvicorn api:app --reload)
|-- nyx_diaricat_client.py     # Consumer SSE de Diaricat Live
|-- requirements.txt           # Dependencias Python
|-- .env                       # ANTHROPIC_API_KEY, APIFY_TOKEN
|-- .gitignore                 # .env, __pycache__, info/
|
|-- core/                      # Modulos de aplicacion
|   |-- __init__.py
|   |-- store.py               # DataStore: acceso centralizado a info/
|   |-- signals.py             # Senales derivadas (brecha, tasa real, presion)
|   |-- classifier.py          # Clasificador noticias -> eventos tipados
|   +-- agent.py               # >> AGENTE IA << (implementar aca)
|
|-- info/                      # 67 archivos, 8.19 MB de data descargada
|   |-- apis/     (21 files)   # Dolar, BCRA, riesgo pais, series, NASA
|   |-- twitter/  (13 files)   # 7,414 tweets
|   |-- articles/ (6 files)    # 135 articulos
|   |-- rag/      (16 files)   # 73 resultados RAG
|   |-- news/     (6 files)    # 128 RSS items
|   |-- reddit/   (4 files)    # 67 posts
|   |-- trends/   (1 file)     # Google Trends AR
|   |-- _quick_load.json       # Data esencial en 1 archivo
|   |-- _news_digest.json      # 336 noticias consolidadas
|   +-- _index.json            # Indice completo
|
|-- data/                      # Archivos de referencia y demo
|   |-- nyx-events-demo.json   # 18 eventos demo pre-clasificados
|   |-- nyx-apify-actors.json  # Actors Apify configurados
|   +-- nyx-preload-data.json  # Data pre-consolidada
|
+-- scripts/                   # Scripts de descarga y testing
    |-- download_all_apis.py   # Descarga todas las APIs
    |-- download_all_apify.py  # Descarga Apify (twitter, reddit, etc)
    |-- organize_info.py       # Genera _index, _quick_load, _news_digest
    |-- build_final_files.py   # Genera archivos en data/
    +-- test-results/          # JSONs de resultados de tests"""))

    story.append(PageBreak())

    # ── 9. TIPS HACKATHON ────────────────────────
    story.append(h1("9. Tips para el Hackathon"))
    story.append(spacer(6))

    story.append(h2("Queries de demo preparadas"))
    story.append(p("Tener estas queries listas para la presentacion:"))
    demos = [
        ["#", "Query", "Que muestra"],
        ["1", "Que esta pasando con el dolar hoy?",
         "Usa solo data local. Muestra brecha, blue, oficial."],
        ["2", "Dame un resumen del riesgo economico de Argentina esta semana",
         "Usa senales + noticias + eventos. Impactante."],
        ["3", "Que esta diciendo la gente en Twitter sobre la inflacion?",
         "Busca en 7414 tweets descargados. Sentimiento."],
        ["4", "Hubo algun paro o conflicto sindical reciente?",
         "Clasifica eventos sindical, muestra urgencias."],
        ["5", "Que paso hoy con el BCRA? (live)",
         "Busca local primero, luego Apify live. Muestra budget."],
    ]
    story.append(make_table(demos[0], demos[1:], col_widths=[20, 220, 200]))
    story.append(spacer(10))

    story.append(h2("Puntos para mostrar en la demo"))
    story.append(bullet("<b>verbose=True</b> — Muestra el razonamiento del agente en tiempo real"))
    story.append(bullet("<b>Local First</b> — El 80% de queries no gasta ni un centavo en Apify"))
    story.append(bullet("<b>Budget Guard</b> — Arquitectura de costos responsable (max $0.50/query)"))
    story.append(bullet("<b>7 tools especializados</b> — Claude decide cual usar segun la pregunta"))
    story.append(bullet("<b>Senales derivadas</b> — Brecha, tasa real, presion: datos que ningun API da"))
    story.append(bullet("<b>Clasificador de eventos</b> — 336 noticias -> mapa de riesgo por tipo y urgencia"))
    story.append(bullet("<b>Diaricat Live</b> — Stream SSE de audio en tiempo real (en paralelo)"))
    story.append(spacer(10))

    story.append(h2("Orden sugerido para la presentacion"))
    story.append(p("1. Mostrar <b>python main.py</b> — resumen instantaneo del estado economico"))
    story.append(p("2. Levantar <b>python api.py</b> — mostrar endpoints en el browser"))
    story.append(p("3. Demo del agente con <b>verbose=True</b> — 2-3 queries preparadas"))
    story.append(p("4. Mostrar una query que use <b>Apify live</b> — se ve el budget en accion"))
    story.append(p("5. Si hay tiempo: Diaricat Live stream en paralelo"))
    story.append(spacer(10))

    story.append(h2("Checklist pre-demo"))
    checklist = [
        ["", "Item", "Comando de verificacion"],
        ["[ ]", "Python + deps instalados", "pip install -r requirements.txt"],
        ["[ ]", ".env con ANTHROPIC_API_KEY", "cat .env"],
        ["[ ]", ".env con APIFY_TOKEN", "cat .env"],
        ["[ ]", "main.py funciona", "python main.py"],
        ["[ ]", "api.py levanta", "python api.py"],
        ["[ ]", "info/ tiene datos", "python -c \"from core.store import DataStore; print(DataStore().summary())\""],
        ["[ ]", "Agente responde", "python -c \"from core.agent import NyxAgent; ...\""],
        ["[ ]", "Internet disponible", "Para busquedas Apify live"],
    ]
    story.append(make_table(checklist[0], checklist[1:], col_widths=[25, 180, 235]))

    story.append(spacer(20))
    story.append(hr())
    story.append(Paragraph("Nyx Terminal - Hackathon Abril 2026", ParagraphStyle(
        "Footer", parent=sSmall, alignment=TA_CENTER)))

    doc.build(story)
    print(f"PDF generado: {OUT}")


if __name__ == "__main__":
    build()
