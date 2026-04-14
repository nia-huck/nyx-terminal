"""Nyx Terminal — Agente inteligente con Claude + data local + PostgreSQL + Apify live.

Flujo:
  1. Recibe pregunta del usuario
  2. Busca contexto previo en PostgreSQL (si habilitado)
  3. Claude decide que tools usar (local gratis, DB, Apify si necesita)
  4. Budget guard: max USD por consulta a Apify
  5. Sintetiza respuesta final
  6. Guarda insights en PostgreSQL (si habilitado)

Uso:
  agent = NyxAgent.from_config()
  response = agent.ask("Que esta pasando con el dolar hoy?")
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

import anthropic

from core.store import DataStore
from core.signals import all_signals, brecha_cambiaria, tasa_real, presion_cambiaria
from core.classifier import classify_all, classify_text
from core import math_engine
from core.config import get_config
from core.mcp_apify import ApifyMCPServer

# ── Costos estimados por actor Apify ──────────────
# Starter plan: $29/mes = ~$0.96/dia
# Estos son estimados conservadores por run
APIFY_COST_ESTIMATES = {
    "apify/rag-web-browser": 0.02,       # ~$0.01-0.03 por query
    "xtdata/twitter-x-scraper": 0.05,    # ~$0.03-0.08 por busqueda
    "apify/google-trends-scraper": 0.03,  # ~$0.02-0.05 por batch
    "trudax/reddit-scraper-lite": 0.02,   # ~$0.01-0.03 por sub
    "lukaskrivka/article-extractor-smart": 0.03,  # ~$0.02-0.05 por site
}

# ── System prompt ─────────────────────────────────
MODE_PROMPTS = {
    "analyst": """Respondé de forma concisa y con datos concretos.
Citá numeros exactos. Priorizá data local sobre busquedas live.
Formato: párrafos cortos con datos clave resaltados.""",

    "researcher": """Investigá en profundidad. Cruzá multiples fuentes.
Usá Apify si necesitas datos mas recientes. Escribí analisis extenso.
Incluí comparaciones historicas y proyecciones. Guardá tus conclusiones como contexto.""",

    "monitor": """Detectá cambios relevantes y generá alertas.
Compará con datos anteriores. Si encontrás algo notable, guardalo como insight o alerta.
Priorizá deteccion de riesgos y oportunidades.""",
}

SYSTEM_PROMPT = """Sos {persona}, un analista economico argentino experto. Tu trabajo es responder consultas sobre la economia argentina usando datos reales y actualizados.

MODO: {mode_desc}

REGLAS:
1. SIEMPRE empezá buscando en la data local (consultar_datos, consultar_senales, consultar_analisis). Es gratis e instantaneo.
2. Si hay PostgreSQL habilitado, usá buscar_db para encontrar contexto previo, noticias relevantes y tweets.
3. SOLO usá busqueda_web o busqueda_twitter si la data local no alcanza.
4. Cada busqueda live cuesta plata. Usa MAXIMO {max_live} busquedas live por consulta.
5. Respondé en {language}. Citá numeros especificos.
6. Cuando des contexto, mencioná tendencias de los ultimos 30 dias.
7. Si detectas riesgo alto, decilo claro con nivel de urgencia.
8. Si descubris algo nuevo e importante, usá guardar_contexto para que lo recuerdes en futuras consultas.
9. CITA TUS FUENTES: cuando uses datos de buscar_db, mencioná la fuente y URL. Ej: "segun Ambito (url)" o "un tweet de @usuario".

DATOS DISPONIBLES LOCALMENTE:
- Dolar (7 tipos, 90 dias historial): blue, oficial, MEP, CCL, mayorista, cripto, tarjeta
- BCRA: reservas, tasas (BADLAR, TM20), base monetaria, circulacion, depositos, prestamos, CDS 5 anos
- Riesgo pais: actual + 90 dias historial
- Inflacion mensual: 24 meses + IPC nacional
- Series: IPC nucleo, EMAE (actividad economica), tipo cambio nominal
- Tasas plazo fijo: 30 entidades con TNA
- Rendimientos crypto: 11 plataformas, stablecoins y crypto
- Noticias: 336 items de RSS + articulos + RAG de 15 temas
- Twitter: 7,414 tweets de 12 busquedas economicas
- Reddit: r/merval + r/argentina economia
- Google Trends AR: 15 terminos economicos

ANALISIS MATEMATICO DISPONIBLE (tool: consultar_analisis):
- indice_nyx: score compuesto de riesgo 0-100 con 8 variables ponderadas
- dolar_velocidad: variacion 7d/30d/90d, volatilidad, min/max para cada tipo
- dolar_spreads: spreads entre tipos (blue/MEP/CCL), convergencia
- dolar_implicito: base monetaria / reservas = tipo de cambio teorico
- crawling_peg: velocidad de devaluacion del oficial (diaria/mensual/anual)
- inflacion: interanual compuesta, aceleracion, tendencia, anualizada
- actividad_emae: crecimiento MoM y YoY, estado de la economia
- tasas_reales: tasa real para cada tipo (BADLAR, TM20, etc.)
- carry_trade: retorno del carry trade (plazo fijo vs devaluacion)
- ranking_plazo_fijo: mejores tasas por entidad
- ranking_crypto: mejores rendimientos por moneda y plataforma
- riesgo_pais: analisis completo + CDS + probabilidad de default
- reservas_velocidad: USD/dia de ganancia o perdida
- expansion_monetaria: base monetaria vs inflacion, presion futura
- poder_adquisitivo: erosion del peso en distintos plazos
- resumen_ejecutivo: resumen textual de todos los indicadores
- reporte_completo: todos los analisis en un solo JSON

IMPORTANTE: Para analisis macro o preguntas complejas, usa consultar_analisis ADEMAS de consultar_datos. El motor matematico cruza datos y calcula metricas que los datos crudos no tienen.

Fecha de hoy: {fecha}
"""


# ── Tool definitions para Claude ──────────────────

LOCAL_TOOLS = [
    {
        "name": "consultar_datos",
        "description": "Consulta datos economicos locales. Categorias: dolar, bcra, riesgo_pais, inflacion, series. Para dolar se puede especificar tipo (blue, oficial, mep, ccl). Para bcra se puede especificar variable (reservas_internacionales, tasa_badlar, base_monetaria, etc).",
        "input_schema": {
            "type": "object",
            "properties": {
                "categoria": {
                    "type": "string",
                    "enum": ["dolar", "bcra", "riesgo_pais", "inflacion", "series"],
                    "description": "Categoria de datos a consultar"
                },
                "detalle": {
                    "type": "string",
                    "description": "Subcategoria o variable especifica. Ej: 'blue', 'reservas_internacionales', 'tasa_badlar'"
                },
                "dias": {
                    "type": "integer",
                    "description": "Cantidad de dias de historial (default 30)",
                    "default": 30
                }
            },
            "required": ["categoria"]
        }
    },
    {
        "name": "consultar_senales",
        "description": "Calcula senales derivadas del cruce de datos: brecha cambiaria (blue vs oficial), tasa real (BADLAR vs inflacion), tendencia de reservas, indicador de presion cambiaria (0-100). Usar para analisis macro.",
        "input_schema": {
            "type": "object",
            "properties": {
                "senal": {
                    "type": "string",
                    "enum": ["todas", "brecha", "tasa_real", "reservas", "presion"],
                    "description": "Senal especifica o 'todas'"
                }
            },
            "required": ["senal"]
        }
    },
    {
        "name": "consultar_noticias",
        "description": "Busca en las 336 noticias descargadas de RSS, articulos y RAG. Puede filtrar por fuente o buscar por texto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fuente": {
                    "type": "string",
                    "description": "Filtrar por fuente: rss_ambito_economia, rss_cronista, article_infobae_economia, rag_noticias_economia, etc. Omitir para todas."
                },
                "buscar": {
                    "type": "string",
                    "description": "Texto a buscar en titulos y resumenes"
                },
                "limite": {
                    "type": "integer",
                    "description": "Maximo de resultados (default 10)",
                    "default": 10
                }
            },
            "required": []
        }
    },
    {
        "name": "consultar_eventos",
        "description": "Obtiene eventos clasificados por tipo (sindical, regulatorio, economico, politico, climatico) con nivel de urgencia. Basado en noticias reales clasificadas automaticamente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {
                    "type": "string",
                    "enum": ["todos", "sindical", "regulatorio", "economico", "politico", "climatico"],
                    "description": "Filtrar por tipo de evento"
                },
                "min_urgencia": {
                    "type": "integer",
                    "description": "Urgencia minima (1-10, default 1)",
                    "default": 1
                },
                "limite": {
                    "type": "integer",
                    "description": "Maximo de resultados (default 10)",
                    "default": 10
                }
            },
            "required": []
        }
    },
    {
        "name": "consultar_social",
        "description": "Busca en tweets (7414), reddit (67 posts) o Google Trends descargados. Para twitter se puede filtrar por query original: bcra, dolar_blue, inflacion, economia_ar, milei_economia, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "red": {
                    "type": "string",
                    "enum": ["twitter", "reddit", "trends"],
                    "description": "Red social a consultar"
                },
                "query": {
                    "type": "string",
                    "description": "Para twitter: nombre de la busqueda (bcra, dolar_blue, inflacion, etc). Para reddit: subreddit (merval_hot, merval_new, argentina_economia)"
                },
                "buscar": {
                    "type": "string",
                    "description": "Texto a buscar dentro de los resultados"
                },
                "limite": {
                    "type": "integer",
                    "description": "Maximo de resultados (default 10)",
                    "default": 10
                }
            },
            "required": ["red"]
        }
    },
]

ANALISIS_TOOL = {
    "name": "consultar_analisis",
    "description": "Motor de analisis matematico avanzado. Calcula metricas derivadas que no estan directamente en los datos crudos. Incluye: indice Nyx de riesgo (0-100), velocidad/volatilidad/spreads del dolar, dolar implicito, carry trade multi-dolar, inflacion interanual+core vs headline, sentiment social, tasa de politica monetaria, multiplicador monetario, depositos tendencia, poder adquisitivo. Usar para analisis profundo.",
    "input_schema": {
        "type": "object",
        "properties": {
            "analisis": {
                "type": "string",
                "enum": [
                    "reporte_completo",
                    "indice_nyx",
                    "resumen_ejecutivo",
                    "dolar_velocidad",
                    "dolar_spreads",
                    "dolar_blend",
                    "dolar_implicito",
                    "dolar_euro",
                    "crawling_peg",
                    "inflacion",
                    "inflacion_core_vs_headline",
                    "inflacion_extendida",
                    "actividad_emae",
                    "actividad_emae_ajustada",
                    "tasas_reales",
                    "tasa_politica",
                    "carry_trade",
                    "carry_trade_multi",
                    "ranking_plazo_fijo",
                    "ranking_crypto",
                    "riesgo_pais",
                    "reservas_velocidad",
                    "expansion_monetaria",
                    "multiplicador_monetario",
                    "depositos_ratio",
                    "depositos_tendencia",
                    "sentiment_social",
                    "noticias_volumen",
                    "poder_adquisitivo",
                ],
                "description": "Tipo de analisis a ejecutar"
            }
        },
        "required": ["analisis"]
    }
}

DB_TOOLS = [
    {
        "name": "buscar_db",
        "description": "Busca en la base de datos PostgreSQL usando full-text search. Busca en noticias (407), tweets (7002), reddit, eventos y contexto previo del agente. Cada resultado incluye fuente y URL para citar. Usar para encontrar info relevante y citar fuentes concretas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto a buscar (en español)"
                },
                "limite": {
                    "type": "integer",
                    "description": "Max resultados (default 10)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "guardar_contexto",
        "description": "Guarda un insight, alerta o tendencia que descubriste durante tu analisis. Esto persiste en la base de datos y estara disponible en futuras consultas. Usar cuando descubras algo nuevo e importante.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {
                    "type": "string",
                    "enum": ["insight", "alerta", "tendencia"],
                    "description": "Tipo de contexto: insight (conclusion), alerta (riesgo detectado), tendencia (patron)"
                },
                "titulo": {
                    "type": "string",
                    "description": "Titulo corto del hallazgo"
                },
                "contenido": {
                    "type": "string",
                    "description": "Descripcion detallada del hallazgo"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags relevantes (ej: dolar, inflacion, riesgo)"
                }
            },
            "required": ["tipo", "titulo", "contenido"]
        }
    },
]

LIVE_TOOLS = [
    {
        "name": "busqueda_web",
        "description": "BUSQUEDA LIVE — Busca en la web en tiempo real usando Apify RAG Web Browser. CUESTA DINERO (~$0.02). Solo usar si la data local no tiene lo que necesitas. Ideal para noticias de ultima hora o temas muy especificos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query de busqueda (en espanol, especifico)"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximo de resultados (default 5, max 10)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "busqueda_twitter",
        "description": "BUSQUEDA LIVE — Busca tweets en tiempo real usando Apify Twitter scraper. CUESTA DINERO (~$0.05). Solo usar si necesitas tweets muy recientes sobre un tema especifico que no esta en la data descargada.",
        "input_schema": {
            "type": "object",
            "properties": {
                "terminos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Terminos de busqueda"
                },
                "max_tweets": {
                    "type": "integer",
                    "description": "Maximo de tweets (default 20, max 50)",
                    "default": 20
                }
            },
            "required": ["terminos"]
        }
    },
]


class NyxAgent:
    """Agente Nyx Terminal con Claude + data local + PostgreSQL + Apify live."""

    def __init__(
        self,
        anthropic_key: str,
        apify_token: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        max_budget_per_query: float = 0.50,
        max_live_calls: int = 2,
        max_iterations: int = 8,
        mode: str = "analyst",
        language: str = "es-AR",
        save_context: bool = True,
        use_db_context: bool = True,
        db_context_limit: int = 10,
        db_enabled: bool = True,
        apify_enabled: bool = True,
        system_prompt_extra: str = "",
        persona: str = "Nyx",
    ):
        self.client = anthropic.Anthropic(api_key=anthropic_key)
        self.mcp_apify = ApifyMCPServer(
            apify_token=apify_token,
            persist_to_db=save_context and db_enabled,
        ) if apify_token and apify_enabled else None
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_budget = max_budget_per_query
        self.max_live_calls = max_live_calls
        self.max_iterations = max_iterations
        self.mode = mode
        self.language = language
        self.save_context = save_context and db_enabled
        self.use_db_context = use_db_context and db_enabled
        self.db_context_limit = db_context_limit
        self.db_enabled = db_enabled
        self.system_prompt_extra = system_prompt_extra
        self.persona = persona
        self.store = DataStore()
        self._spent = 0.0
        self._live_calls = 0
        self._citations: list[dict] = []

    @classmethod
    def from_config(cls, **overrides) -> "NyxAgent":
        """Crea un agente desde la configuracion guardada."""
        cfg = get_config()
        params = {
            "anthropic_key": cfg["anthropic_api_key"],
            "apify_token": cfg["apify_token"],
            "model": cfg["model"],
            "max_tokens": cfg["max_tokens"],
            "temperature": cfg["temperature"],
            "max_budget_per_query": cfg["max_budget_per_query"],
            "max_live_calls": cfg["max_live_calls"],
            "max_iterations": cfg["max_iterations"],
            "mode": cfg["mode"],
            "language": cfg["language"],
            "save_context": cfg["save_context"],
            "use_db_context": cfg["use_db_context"],
            "db_context_limit": cfg["db_context_limit"],
            "db_enabled": cfg["db_enabled"],
            "apify_enabled": cfg["apify_enabled"],
            "system_prompt_extra": cfg["system_prompt_extra"],
            "persona": cfg["persona"],
        }
        params.update(overrides)
        return cls(**params)

    def _reset_budget(self):
        self._spent = 0.0
        self._live_calls = 0
        self._citations: list[dict] = []

    def _deduplicate_citations(self) -> list[dict]:
        seen: set[str] = set()
        result = []
        for c in self._citations:
            url = c.get("url", "")
            if url and url not in seen:
                seen.add(url)
                result.append(c)
        return result[:8]

    # ── Ejecutar tools locales (gratis) ───────────

    def _exec_consultar_datos(self, params: dict) -> dict:
        cat = params.get("categoria")
        detalle = params.get("detalle", "")
        dias = params.get("dias", 30)

        if cat == "dolar":
            if detalle:
                hist = self.store.dolar_historial(detalle, dias)
                current = None
                for d in self.store.dolar_actual():
                    if detalle.lower() in (d.get("nombre", "") + d.get("casa", "")).lower():
                        current = d
                        break
                return {"actual": current, "historial_dias": len(hist), "historial": hist[-10:]}
            return {"tipos": self.store.dolar_actual()}

        elif cat == "bcra":
            if detalle:
                var = self.store.bcra_variable(detalle)
                return {"variable": detalle, "data": var} if var else {"error": f"Variable '{detalle}' no encontrada"}
            return {
                "reservas": self.store.reservas(),
                "badlar": self.store.tasa_badlar(),
                "base_monetaria": self.store.base_monetaria(),
            }

        elif cat == "riesgo_pais":
            return {
                "actual": self.store.riesgo_pais(),
                "historial": self.store.riesgo_pais_historial(dias),
            }

        elif cat == "inflacion":
            return {"mensual": self.store.inflacion_mensual(dias)}

        elif cat == "series":
            if detalle:
                return {"serie": detalle, "data": self.store.serie(detalle)}
            return {"series_disponibles": ["ipc_nucleo", "emae", "ipc_nacional", "tipo_cambio_nominal"]}

        return {"error": f"Categoria '{cat}' no reconocida"}

    def _exec_consultar_senales(self, params: dict) -> dict:
        senal = params.get("senal", "todas")
        if senal == "todas":
            return all_signals(self.store)
        elif senal == "brecha":
            return brecha_cambiaria(self.store) or {"error": "No se pudo calcular"}
        elif senal == "tasa_real":
            return tasa_real(self.store) or {"error": "No se pudo calcular"}
        elif senal == "reservas":
            from core.signals import tendencia_reservas
            return tendencia_reservas(self.store) or {"error": "No se pudo calcular"}
        elif senal == "presion":
            return presion_cambiaria(self.store)
        return {"error": f"Senal '{senal}' no reconocida"}

    def _exec_consultar_noticias(self, params: dict) -> dict:
        fuente = params.get("fuente")
        buscar = params.get("buscar", "").lower()
        limite = min(params.get("limite", 10), 30)

        items = self.store.noticias(fuente)
        if buscar:
            items = [
                i for i in items
                if buscar in (i.get("titulo", "") + i.get("resumen", "") + i.get("title", "") + i.get("text", "")).lower()
            ]

        # Build a url→source_key map so we can assign the fuente name to each citation
        sources = self.store.news_digest.get("sources", {})
        url_to_source: dict[str, str] = {}
        src_keys = [fuente] if fuente else list(sources.keys())
        for src_key in src_keys:
            for it in sources.get(src_key, []):
                u = it.get("url") or it.get("link")
                if u:
                    url_to_source[u] = src_key

        for item in items[:limite]:
            url = item.get("url") or item.get("link")
            if url:
                src_key = url_to_source.get(url, "")
                self._citations.append({
                    "titulo": (item.get("titulo") or item.get("title", ""))[:80],
                    "url": url,
                    "fuente": src_key,
                })
        return {"total": len(items), "items": items[:limite]}

    def _exec_consultar_eventos(self, params: dict) -> dict:
        tipo = params.get("tipo", "todos")
        min_urg = params.get("min_urgencia", 1)
        limite = min(params.get("limite", 10), 30)

        noticias = self.store.noticias()
        events = classify_all(noticias)

        if tipo != "todos":
            events = [e for e in events if e["tipo"] == tipo]
        events = [e for e in events if e["urgencia"] >= min_urg]

        return {"total": len(events), "eventos": events[:limite]}

    def _exec_consultar_social(self, params: dict) -> dict:
        red = params.get("red")
        query = params.get("query")
        buscar = params.get("buscar", "").lower()
        limite = min(params.get("limite", 10), 30)

        if red == "twitter":
            items = self.store.tweets(query)
            if buscar:
                items = [t for t in items if buscar in t.get("text", "").lower()]
            return {"total": len(items), "tweets": items[:limite]}

        elif red == "reddit":
            items = self.store.reddit(query)
            if buscar:
                items = [r for r in items if buscar in (r.get("title", "") + r.get("body", "")).lower()]
            return {"total": len(items), "posts": items[:limite]}

        elif red == "trends":
            return {"trends": self.store.trends()}

        return {"error": f"Red '{red}' no reconocida"}

    # ── Ejecutar analisis matematico (gratis) ──────

    def _exec_consultar_analisis(self, params: dict) -> dict:
        analisis = params.get("analisis", "indice_nyx")
        handlers = {
            "reporte_completo": lambda: math_engine.reporte_completo(self.store),
            "indice_nyx": lambda: math_engine.indice_nyx(self.store),
            "resumen_ejecutivo": lambda: {"texto": math_engine.resumen_ejecutivo(self.store)},
            "dolar_velocidad": lambda: math_engine.dolar_velocidad(self.store),
            "dolar_spreads": lambda: math_engine.dolar_spreads(self.store),
            "dolar_blend": lambda: math_engine.dolar_blend(self.store),
            "dolar_implicito": lambda: math_engine.dolar_implicito(self.store),
            "dolar_euro": lambda: math_engine.dolar_euro(self.store),
            "crawling_peg": lambda: math_engine.crawling_peg(self.store),
            "inflacion": lambda: math_engine.inflacion_analisis(self.store),
            "inflacion_core_vs_headline": lambda: math_engine.inflacion_core_vs_headline(self.store),
            "inflacion_extendida": lambda: math_engine.inflacion_extendida(self.store),
            "actividad_emae": lambda: math_engine.actividad_emae(self.store),
            "actividad_emae_ajustada": lambda: math_engine.actividad_emae_ajustada(self.store),
            "tasas_reales": lambda: math_engine.tasas_reales(self.store),
            "tasa_politica": lambda: math_engine.tasa_politica(self.store),
            "carry_trade": lambda: math_engine.carry_trade(self.store),
            "carry_trade_multi": lambda: math_engine.carry_trade_multi(self.store),
            "ranking_plazo_fijo": lambda: {"ranking": math_engine.ranking_plazo_fijo(self.store)},
            "ranking_crypto": lambda: math_engine.ranking_crypto_yields(self.store),
            "riesgo_pais": lambda: math_engine.riesgo_pais_analisis(self.store),
            "reservas_velocidad": lambda: math_engine.reservas_velocidad(self.store),
            "expansion_monetaria": lambda: math_engine.expansion_monetaria(self.store),
            "multiplicador_monetario": lambda: math_engine.multiplicador_monetario(self.store),
            "depositos_ratio": lambda: math_engine.depositos_ratio(self.store),
            "depositos_tendencia": lambda: math_engine.depositos_tendencia(self.store),
            "sentiment_social": lambda: math_engine.sentiment_social(self.store),
            "noticias_volumen": lambda: math_engine.noticias_volumen(self.store),
            "poder_adquisitivo": lambda: math_engine.poder_adquisitivo(self.store),
        }
        fn = handlers.get(analisis)
        if not fn:
            return {"error": f"Analisis '{analisis}' no reconocido"}
        return fn() or {"error": "No hay datos suficientes para este analisis"}

    # ── Ejecutar tools de base de datos (gratis) ──

    def _exec_buscar_db(self, params: dict) -> dict:
        if not self.db_enabled:
            return {"error": "PostgreSQL no habilitado"}
        try:
            from core.context_writer import buscar_en_todo
            query = params.get("query", "")
            limite = min(params.get("limite", 10), 30)
            raw = buscar_en_todo(query, limite)
            # Format with citation data
            results = []
            for r in raw:
                entry = {
                    "tipo": r.get("tabla", "?"),
                    "titulo": r.get("titulo", "")[:200],
                    "resumen": r.get("resumen", "")[:500] if r.get("resumen") else None,
                    "fuente": r.get("fuente", ""),
                    "url": r.get("url"),
                    "fecha": str(r.get("fecha", "")) if r.get("fecha") else None,
                    "relevancia": round(r.get("rank", 0), 3),
                }
                results.append(entry)
            for r in results:
                if r.get("url"):
                    self._citations.append({
                        "titulo": r["titulo"][:80],
                        "url": r["url"],
                        "fuente": r.get("fuente", ""),
                    })
            return {"query": query, "total": len(results), "resultados": results}
        except Exception as e:
            return {"error": f"DB error: {str(e)[:200]}"}

    def _exec_guardar_contexto(self, params: dict) -> dict:
        if not self.save_context:
            return {"ok": False, "reason": "Guardar contexto deshabilitado"}
        try:
            from core import context_writer
            tipo = params.get("tipo", "insight")
            titulo = params.get("titulo", "")
            contenido = params.get("contenido", "")
            tags = params.get("tags", [])

            handlers = {
                "insight": context_writer.guardar_insight,
                "alerta": context_writer.guardar_alerta,
                "tendencia": context_writer.guardar_tendencia,
            }
            fn = handlers.get(tipo, context_writer.guardar_insight)
            ctx_id = fn(titulo, contenido, tags=tags)
            return {"ok": True, "id": ctx_id, "tipo": tipo}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    # ── Ejecutar tools live via MCP (cuestan plata) ─

    def _exec_busqueda_web(self, params: dict) -> dict:
        cost = APIFY_COST_ESTIMATES["apify/rag-web-browser"]
        if self._spent + cost > self.max_budget:
            return {"error": f"Budget excedido (gastado: ${self._spent:.2f}, limite: ${self.max_budget:.2f})"}
        if self._live_calls >= self.max_live_calls:
            return {"error": f"Maximo de {self.max_live_calls} busquedas live alcanzado"}
        if not self.mcp_apify:
            return {"error": "Apify MCP no configurado"}

        result = self.mcp_apify.call_tool("apify_web_search", {
            "query": params.get("query", ""),
            "max_results": min(params.get("max_results", 5), 10),
        })

        if result.get("isError"):
            return {"error": result.get("error", "MCP error")}

        self._spent += cost
        self._live_calls += 1
        for r in result.get("results", []):
            if r.get("url"):
                self._citations.append({
                    "titulo": r.get("title", r.get("url", ""))[:80],
                    "url": r["url"],
                    "fuente": "web",
                })
        return {"query": params.get("query"), "results": result.get("results", []), "cost": cost, "via": "mcp"}

    def _exec_busqueda_twitter(self, params: dict) -> dict:
        cost = APIFY_COST_ESTIMATES["xtdata/twitter-x-scraper"]
        if self._spent + cost > self.max_budget:
            return {"error": f"Budget excedido (gastado: ${self._spent:.2f}, limite: ${self.max_budget:.2f})"}
        if self._live_calls >= self.max_live_calls:
            return {"error": f"Maximo de {self.max_live_calls} busquedas live alcanzado"}
        if not self.mcp_apify:
            return {"error": "Apify MCP no configurado"}

        result = self.mcp_apify.call_tool("apify_twitter_search", {
            "terms": params.get("terminos", []),
            "max_tweets": min(params.get("max_tweets", 20), 50),
        })

        if result.get("isError"):
            return {"error": result.get("error", "MCP error")}

        self._spent += cost
        self._live_calls += 1
        return {"terminos": params.get("terminos"), "tweets": result.get("tweets", []), "cost": cost, "via": "mcp"}

    # ── Router de tools ───────────────────────────

    def _execute_tool(self, name: str, params: dict) -> str:
        handlers = {
            "consultar_datos": self._exec_consultar_datos,
            "consultar_senales": self._exec_consultar_senales,
            "consultar_noticias": self._exec_consultar_noticias,
            "consultar_eventos": self._exec_consultar_eventos,
            "consultar_social": self._exec_consultar_social,
            "consultar_analisis": self._exec_consultar_analisis,
            "buscar_db": self._exec_buscar_db,
            "guardar_contexto": self._exec_guardar_contexto,
            "busqueda_web": self._exec_busqueda_web,
            "busqueda_twitter": self._exec_busqueda_twitter,
        }
        handler = handlers.get(name)
        if not handler:
            return json.dumps({"error": f"Tool '{name}' no existe"})

        result = handler(params)
        return json.dumps(result, ensure_ascii=False, default=str)

    # ── Loop principal del agente ─────────────────

    def ask(self, question: str, verbose: bool = False) -> dict:
        """Procesa una pregunta y devuelve respuesta + metadata."""
        self._reset_budget()
        start = time.time()

        # Build system prompt from config
        lang_map = {"es-AR": "espanol argentino", "es": "espanol", "en": "English"}
        mode_desc = MODE_PROMPTS.get(self.mode, MODE_PROMPTS["analyst"])
        system = SYSTEM_PROMPT.format(
            persona=self.persona,
            mode_desc=mode_desc,
            max_live=self.max_live_calls,
            language=lang_map.get(self.language, self.language),
            fecha=datetime.now().strftime("%Y-%m-%d"),
        )
        if self.system_prompt_extra:
            system += f"\n\nINSTRUCCIONES ADICIONALES:\n{self.system_prompt_extra}"

        # Build tools list
        tools = LOCAL_TOOLS + [ANALISIS_TOOL]
        if self.db_enabled:
            tools += DB_TOOLS
        if self.mcp_apify:
            tools += LIVE_TOOLS

        # Pre-inject DB context if enabled
        user_content = question
        if self.use_db_context:
            try:
                from core.context_writer import buscar_en_todo, obtener_alertas_activas
                ctx = buscar_en_todo(question, self.db_context_limit)
                alertas = obtener_alertas_activas(5)
                if ctx or alertas:
                    ctx_text = "\n\n--- CONTEXTO PREVIO (de tu base de datos) ---\n"
                    if alertas:
                        ctx_text += "ALERTAS ACTIVAS:\n"
                        for a in alertas:
                            ctx_text += f"  [{a.get('relevancia', '?')}] {a['titulo']}: {a['contenido'][:200]}\n"
                    if ctx:
                        ctx_text += f"\nBUSQUEDA RELEVANTE ({len(ctx)} resultados):\n"
                        for r in ctx[:5]:
                            url = r.get("url", "")
                            url_part = f" — {url}" if url else ""
                            ctx_text += f"  [{r['tabla']}] {r['titulo'][:100]}{url_part}\n"
                            if url:
                                self._citations.append({
                                    "titulo": r["titulo"][:80],
                                    "url": url,
                                    "fuente": r.get("fuente", r.get("tabla", "")),
                                })
                    ctx_text += "--- FIN CONTEXTO ---\n"
                    user_content = question + ctx_text
            except Exception:
                pass  # DB not available, continue without context

        messages = [{"role": "user", "content": user_content}]

        tool_calls_log = []
        iterations = 0
        max_iterations = self.max_iterations

        while iterations < max_iterations:
            iterations += 1

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system,
                    tools=tools,
                    messages=messages,
                )
            except anthropic.BadRequestError as e:
                msg = str(e)
                if "credit balance" in msg or "Plans & Billing" in msg:
                    return {"respuesta": "Error: saldo insuficiente en la cuenta de la API de Anthropic. Recarga creditos en console.anthropic.com → Billing.", "tool_calls": [], "live_calls": 0, "apify_spent": 0, "iterations": iterations, "elapsed_s": 0, "model": self.model, "mode": self.mode, "db_enabled": self.db_enabled}
                raise
            except anthropic.AuthenticationError:
                return {"respuesta": "Error: API key de Anthropic invalida o expirada. Revisa el archivo .env.", "tool_calls": [], "live_calls": 0, "apify_spent": 0, "iterations": iterations, "elapsed_s": 0, "model": self.model, "mode": self.mode, "db_enabled": self.db_enabled}
            except anthropic.PermissionDeniedError:
                return {"respuesta": "Error: acceso denegado por la API de Anthropic. Verifica permisos y creditos en console.anthropic.com.", "tool_calls": [], "live_calls": 0, "apify_spent": 0, "iterations": iterations, "elapsed_s": 0, "model": self.model, "mode": self.mode, "db_enabled": self.db_enabled}

            # Check if done (no more tool use)
            if response.stop_reason == "end_turn":
                # Extract text response
                text = ""
                for block in response.content:
                    if block.type == "text":
                        text += block.text
                break

            # Process tool calls
            assistant_content = response.content
            tool_results = []

            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    is_live = tool_name in ("busqueda_web", "busqueda_twitter")

                    if verbose:
                        marker = "$" if is_live else ">"
                        print(f"  {marker} {tool_name}({json.dumps(tool_input, ensure_ascii=False)[:100]})")

                    result_str = self._execute_tool(tool_name, tool_input)

                    if verbose and is_live:
                        print(f"    gastado: ${self._spent:.2f} / ${self.max_budget:.2f}")

                    tool_calls_log.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "live": is_live,
                        "cost": APIFY_COST_ESTIMATES.get(
                            {"busqueda_web": "apify/rag-web-browser", "busqueda_twitter": "xtdata/twitter-x-scraper"}.get(tool_name, ""),
                            0
                        ) if is_live else 0,
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            # Add assistant message + tool results to conversation
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        else:
            text = "[Error: se alcanzo el limite de iteraciones]"

        elapsed = time.time() - start

        return {
            "respuesta": text,
            "tool_calls": tool_calls_log,
            "live_calls": self._live_calls,
            "apify_spent": round(self._spent, 3),
            "iterations": iterations,
            "elapsed_s": round(elapsed, 2),
            "model": self.model,
            "mode": self.mode,
            "db_enabled": self.db_enabled,
            "citations": self._deduplicate_citations(),
        }

    def ask_stream(self, question: str):
        """Streaming version — yields SSE events as the agent works.
        Events: {type: "status"|"tool"|"chunk"|"done"|"error", data: ...}
        """
        self._reset_budget()
        start = time.time()

        lang_map = {"es-AR": "espanol argentino", "es": "espanol", "en": "English"}
        mode_desc = MODE_PROMPTS.get(self.mode, MODE_PROMPTS["analyst"])
        system = SYSTEM_PROMPT.format(
            persona=self.persona,
            mode_desc=mode_desc,
            max_live=self.max_live_calls,
            language=lang_map.get(self.language, self.language),
            fecha=datetime.now().strftime("%Y-%m-%d"),
        )
        if self.system_prompt_extra:
            system += f"\n\nINSTRUCCIONES ADICIONALES:\n{self.system_prompt_extra}"

        tools = LOCAL_TOOLS + [ANALISIS_TOOL]
        if self.db_enabled:
            tools += DB_TOOLS
        if self.mcp_apify:
            tools += LIVE_TOOLS

        # Pre-inject DB context
        user_content = question
        if self.use_db_context:
            try:
                from core.context_writer import buscar_en_todo, obtener_alertas_activas
                ctx = buscar_en_todo(question, self.db_context_limit)
                alertas = obtener_alertas_activas(5)
                if ctx or alertas:
                    ctx_text = "\n\n--- CONTEXTO PREVIO ---\n"
                    if alertas:
                        for a in alertas:
                            ctx_text += f"  [{a.get('relevancia', '?')}] {a['titulo']}: {a['contenido'][:200]}\n"
                    if ctx:
                        for r in ctx[:5]:
                            url = r.get("url", "")
                            url_part = f" — {url}" if url else ""
                            ctx_text += f"  [{r['tabla']}] {r['titulo'][:100]}{url_part}\n"
                            if url:
                                self._citations.append({
                                    "titulo": r["titulo"][:80],
                                    "url": url,
                                    "fuente": r.get("fuente", r.get("tabla", "")),
                                })
                    ctx_text += "---\n"
                    user_content = question + ctx_text
                    yield {"type": "status", "data": f"Contexto DB: {len(ctx)} resultados, {len(alertas)} alertas"}
            except Exception:
                pass

        messages = [{"role": "user", "content": user_content}]
        tool_calls_log = []
        iterations = 0

        yield {"type": "status", "data": "Pensando..."}

        while iterations < self.max_iterations:
            iterations += 1

            # Use streaming API
            text_chunks = []
            tool_uses = []


            try:
              stream_ctx = self.client.messages.stream(
                  model=self.model,
                  max_tokens=self.max_tokens,
                  temperature=self.temperature,
                  system=system,
                  tools=tools,
                  messages=messages,
              )
            except anthropic.BadRequestError as e:
                msg = str(e)
                if "credit balance" in msg or "Plans & Billing" in msg:
                    yield {"type": "error", "data": "Saldo insuficiente en la cuenta de la API de Anthropic. Recarga creditos en console.anthropic.com → Billing."}
                else:
                    yield {"type": "error", "data": str(e)[:300]}
                return
            except anthropic.AuthenticationError:
                yield {"type": "error", "data": "API key de Anthropic invalida o expirada. Revisa el archivo .env."}
                return
            except anthropic.PermissionDeniedError:
                yield {"type": "error", "data": "Acceso denegado por Anthropic. Verifica permisos y creditos en console.anthropic.com."}
                return

            try:
              with stream_ctx as stream:
                for event in stream:
                    if hasattr(event, 'type'):
                        if event.type == 'content_block_start':
                            if hasattr(event, 'content_block') and event.content_block.type == 'tool_use':
                                yield {"type": "tool", "data": event.content_block.name}
                        elif event.type == 'text':
                            text_chunks.append(event.text)
                            yield {"type": "chunk", "data": event.text}
                response = stream.get_final_message()
            except anthropic.BadRequestError as e:
                msg = str(e)
                if "credit balance" in msg or "Plans & Billing" in msg:
                    yield {"type": "error", "data": "Saldo insuficiente en la cuenta de la API de Anthropic. Recarga creditos en console.anthropic.com → Billing."}
                else:
                    yield {"type": "error", "data": str(e)[:300]}
                return

            if response.stop_reason == "end_turn":
                break

            # Process tool calls
            assistant_content = response.content
            tool_results = []

            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    is_live = tool_name in ("busqueda_web", "busqueda_twitter")

                    yield {"type": "tool", "data": f"{'$' if is_live else '>'} {tool_name}"}

                    result_str = self._execute_tool(tool_name, tool_input)

                    tool_calls_log.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "live": is_live,
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

            yield {"type": "status", "data": f"Iteracion {iterations}, {len(tool_calls_log)} tools usadas"}

        else:
            yield {"type": "chunk", "data": "[Error: limite de iteraciones alcanzado]"}

        elapsed = time.time() - start
        yield {"type": "done", "data": {
            "tool_calls": tool_calls_log,
            "live_calls": self._live_calls,
            "apify_spent": round(self._spent, 3),
            "iterations": iterations,
            "elapsed_s": round(elapsed, 2),
            "model": self.model,
            "mode": self.mode,
            "citations": self._deduplicate_citations(),
        }}
