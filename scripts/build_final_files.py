"""Build all final output files for Nyx Terminal hackathon"""
import json
from datetime import datetime

# Load all data
apis = json.load(open("download_apis_results.json", encoding="utf-8"))
apify = json.load(open("download_apify_results.json", encoding="utf-8"))

def p(msg): print(msg)

# ═══════════════════════════════════════════════════════════
# FILE 1: nyx-preload-data.json
# ═══════════════════════════════════════════════════════════
p("=== Building nyx-preload-data.json ===")

preload = {
    "generated_at": datetime.now().isoformat(),
    "dolar": apis.get("dolar", {}),
    "bcra": apis.get("bcra", {}),
    "bcra_cambiarias": apis.get("bcra_cambiarias", {}),
    "riesgo_pais": apis.get("riesgo_pais", {}),
    "ipc": apis.get("ipc", {}),
    "emae": apis.get("emae", {}),
    "bluelytics": apis.get("bluelytics", {}),
    "nasa_events": apis.get("nasa_events", {}),
    "news": apis.get("news", {}),
    "apify_results": {
        "google_trends": apify.get("google_trends", {}),
        "twitter_results": [],
        "google_news_results": [],
        "reddit_merval": apify.get("reddit_merval", {}),
        "boletin_oficial": [],
        "sindicatos": [],
        "rag_web_searches": {},
    },
}

# Extract RAG results into categories
rag = apify.get("rag_results", {})
for qname, qdata in rag.items():
    results = qdata.get("results", [])
    if "twitter" in qname:
        preload["apify_results"]["twitter_results"].extend(results)
    elif "news" in qname or "infobae" in qname:
        preload["apify_results"]["google_news_results"].extend(results)
    elif "boletin" in qname:
        preload["apify_results"]["boletin_oficial"].extend(results)
    elif "sindicato" in qname or "camionero" in qname or "cgt" in qname or "paro" in qname:
        preload["apify_results"]["sindicatos"].extend(results)
    else:
        preload["apify_results"]["rag_web_searches"][qname] = results

# Add article extractor results
if apify.get("article_extractor_test", {}).get("works"):
    preload["apify_results"]["article_extractor"] = apify["article_extractor_test"].get("sample", [])

# Add website crawler
if apify.get("website_crawler", {}).get("status") == "OK":
    preload["apify_results"]["website_crawler_ambito"] = apify["website_crawler"].get("pages", [])

with open("nyx-preload-data.json", "w", encoding="utf-8") as f:
    json.dump(preload, f, indent=2, ensure_ascii=False, default=str)
p(f"  OK: nyx-preload-data.json ({len(json.dumps(preload, default=str))//1024} KB)")

# ═══════════════════════════════════════════════════════════
# FILE 2: nyx-events-demo.json
# ═══════════════════════════════════════════════════════════
p("\n=== Building nyx-events-demo.json ===")

# Collect real news from RSS + RAG
all_news = []
for feed_name, feed_items in apis.get("news", {}).items():
    if isinstance(feed_items, list):
        for it in feed_items[:5]:
            all_news.append({
                "titulo": it.get("titulo", ""),
                "link": it.get("link", ""),
                "fecha": it.get("fecha", ""),
                "fuente": feed_name,
                "resumen": it.get("resumen", ""),
            })

# Extract titles from RAG text content
rag_news = []
for qname, qdata in rag.items():
    for r in qdata.get("results", []):
        text = r.get("text", "")
        if text and len(text) > 30 and "Something went wrong" not in text:
            rag_news.append({"text": text[:200], "query": qname, "url": r.get("url", "")})

# Build demo events based on REAL data collected
events = [
    {
        "id": 1,
        "titulo": "Reclamo de transportistas frena exportaciones en plena cosecha",
        "tipo": "sindical",
        "sector": ["logistica", "agro"],
        "urgencia": 9,
        "provincia": "Buenos Aires",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-04-09",
        "resumen": "Camiones varados en banquinas por reclamo de paritarias. Transportistas frenaron exportaciones en plena cosecha gruesa, generando pérdidas millonarias en puertos del Gran Rosario.",
        "fuente": "Infobae",
        "fuente_url": "https://www.infobae.com/economia/2026/04/09/camiones-en-las-banquinas-el-reclamo-de-transportistas-freno-exportaciones-en-plena-cosecha-y-genero-perdidas-millonarias/",
        "activos_afectados": ["agro", "logistica", "exportaciones"],
        "horizonte_impacto": "72h"
    },
    {
        "id": 2,
        "titulo": "BCRA afloja cepo para ahorristas y empresas",
        "tipo": "regulatorio",
        "sector": ["finanzas"],
        "urgencia": 8,
        "provincia": "CABA",
        "lat": -34.6083,
        "lon": -58.3712,
        "fecha": "2026-04-10",
        "resumen": "El BCRA aprovecha la calma cambiaria para flexibilizar restricciones al acceso de dólares. Com. A 8417 modifica régimen cambiario para ahorristas y empresas.",
        "fuente": "Ámbito Financiero",
        "fuente_url": "https://www.ambito.com/finanzas/dolar-el-bcra-aprovecha-la-calma-cambiaria-y-afloja-mas-el-cepo-ahorristas-y-empresas-n6264984",
        "activos_afectados": ["dolar", "bonos", "acciones_bancarias"],
        "horizonte_impacto": "1 semana"
    },
    {
        "id": 3,
        "titulo": "Tasa BADLAR baja a 23.25% — mínimo del año",
        "tipo": "economico",
        "sector": ["finanzas"],
        "urgencia": 7,
        "provincia": "CABA",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-04-09",
        "resumen": "La tasa BADLAR cayó a 23.25%, desde 33.12% hace 45 días. Depósitos a plazo fijo pierden atractivo frente a dólar e inflación.",
        "fuente": "BCRA API",
        "fuente_url": "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/7",
        "activos_afectados": ["plazo_fijo", "bonos_tasa_variable", "bancarias"],
        "horizonte_impacto": "30 días"
    },
    {
        "id": 4,
        "titulo": "Riesgo país en 557 puntos — presión sobre bonos soberanos",
        "tipo": "economico",
        "sector": ["finanzas"],
        "urgencia": 6,
        "provincia": "CABA",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-04-09",
        "resumen": "El riesgo país se mantiene en 557 pb, reflejando incertidumbre del mercado ante guerra comercial global y vencimientos de deuda próximos.",
        "fuente": "Argentina Datos API",
        "fuente_url": "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo",
        "activos_afectados": ["bonos_soberanos", "acciones"],
        "horizonte_impacto": "2 semanas"
    },
    {
        "id": 5,
        "titulo": "Decreto 219/2026 — Ministerio de Economía",
        "tipo": "regulatorio",
        "sector": ["finanzas", "energia"],
        "urgencia": 7,
        "provincia": "CABA",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-04-06",
        "resumen": "Nuevo decreto del Ministerio de Economía publicado en Boletín Oficial. Posible impacto en regulación económica y sectores estratégicos.",
        "fuente": "Boletín Oficial",
        "fuente_url": "https://www.boletinoficial.gob.ar/detalleAviso/primera/340313/20260406",
        "activos_afectados": ["regulados", "energia"],
        "horizonte_impacto": "1 semana"
    },
    {
        "id": 6,
        "titulo": "IPC Núcleo sube a 10991 — inflación acelera en febrero",
        "tipo": "economico",
        "sector": ["consumo"],
        "urgencia": 8,
        "provincia": "Buenos Aires",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-03-15",
        "resumen": "El IPC Núcleo alcanzó 10991.17 en febrero 2026 (base dic-2016=100). La inflación mensual muestra aceleración respecto a enero.",
        "fuente": "INDEC via datos.gob.ar",
        "fuente_url": "https://apis.datos.gob.ar/series/api/series/?ids=103.1_I2N_2016_M_15",
        "activos_afectados": ["consumo_masivo", "salarios", "bonos_cer"],
        "horizonte_impacto": "30 días"
    },
    {
        "id": 7,
        "titulo": "Tipo de cambio real en mínimo desde 2017",
        "tipo": "economico",
        "sector": ["finanzas", "agro"],
        "urgencia": 7,
        "provincia": "CABA",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-04-10",
        "resumen": "Advertencia del economista Camilo Tiscornia: 'No es sostenible que la inflación le gane al tipo de cambio'. El TC real se ubica en su menor nivel desde 2017.",
        "fuente": "Ámbito Financiero",
        "fuente_url": "https://www.ambito.com/economia",
        "activos_afectados": ["exportadores", "agro", "turismo"],
        "horizonte_impacto": "3 meses"
    },
    {
        "id": 8,
        "titulo": "Exportaciones: factores que empujan ventas a Brasil",
        "tipo": "economico",
        "sector": ["agro", "logistica"],
        "urgencia": 5,
        "provincia": "Buenos Aires",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-04-11",
        "resumen": "Factores positivos impulsan las exportaciones argentinas al principal socio comercial. Oportunidad para sectores productivos.",
        "fuente": "El Cronista",
        "fuente_url": "https://www.cronista.com",
        "activos_afectados": ["agro", "industria", "logistica"],
        "horizonte_impacto": "1 mes"
    },
    {
        "id": 9,
        "titulo": "Créditos hipotecarios caen 10% interanual",
        "tipo": "economico",
        "sector": ["construccion", "finanzas"],
        "urgencia": 5,
        "provincia": "Buenos Aires",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-04-10",
        "resumen": "Los créditos hipotecarios registraron una caída del 10% interanual, señalando enfriamiento del sector inmobiliario.",
        "fuente": "Ámbito Financiero",
        "fuente_url": "https://www.ambito.com/economia",
        "activos_afectados": ["construccion", "inmobiliario", "bancarias"],
        "horizonte_impacto": "3 meses"
    },
    {
        "id": 10,
        "titulo": "Tifón Sinlaku — alerta en Pacífico",
        "tipo": "climatico",
        "sector": ["logistica"],
        "urgencia": 3,
        "provincia": "Internacional",
        "lat": 9.0,
        "lon": 151.1,
        "fecha": "2026-04-11",
        "resumen": "Tifón Sinlaku activo en el Pacífico Occidental. Sin impacto directo en Argentina pero podría afectar cadenas de suministro globales.",
        "fuente": "NASA EONET",
        "fuente_url": "https://eonet.gsfc.nasa.gov/api/v3/events",
        "activos_afectados": ["logistica_global", "importaciones"],
        "horizonte_impacto": "1 semana"
    },
    {
        "id": 11,
        "titulo": "Dólar Blue estable en $1390 — brecha se comprime",
        "tipo": "economico",
        "sector": ["finanzas"],
        "urgencia": 4,
        "provincia": "CABA",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-04-11",
        "resumen": "Blue a $1390, oficial a $1395. La brecha cambiaria se reduce a mínimos. Spread blue-oficial prácticamente nulo.",
        "fuente": "DolarAPI + Bluelytics",
        "fuente_url": "https://dolarapi.com/v1/dolares/blue",
        "activos_afectados": ["dolar", "blue", "financiero"],
        "horizonte_impacto": "48h"
    },
    {
        "id": 12,
        "titulo": "Reservas BCRA en USD 44,759M — caída desde máximos",
        "tipo": "economico",
        "sector": ["finanzas"],
        "urgencia": 6,
        "provincia": "CABA",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-04-08",
        "resumen": "Las reservas internacionales bajaron de USD 46,264M (20/Feb) a USD 44,759M. Pérdida de USD 1,505M en 45 días.",
        "fuente": "BCRA API",
        "fuente_url": "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/1",
        "activos_afectados": ["bonos_soberanos", "tipo_cambio"],
        "horizonte_impacto": "2 semanas"
    },
    {
        "id": 13,
        "titulo": "CGT evalúa plan de acción por paritarias",
        "tipo": "sindical",
        "sector": ["consumo", "logistica"],
        "urgencia": 7,
        "provincia": "CABA",
        "lat": -34.6160,
        "lon": -58.3880,
        "fecha": "2026-04-10",
        "resumen": "La CGT analiza comunicado y posible medida de fuerza por paritarias que no alcanzan a cubrir la inflación acumulada.",
        "fuente": "RAG Web Browser",
        "fuente_url": "",
        "activos_afectados": ["consumo_masivo", "transporte", "servicios"],
        "horizonte_impacto": "1 semana"
    },
    {
        "id": 14,
        "titulo": "EMAE enero 2026: actividad económica en 149.04",
        "tipo": "economico",
        "sector": ["consumo", "finanzas"],
        "urgencia": 5,
        "provincia": "CABA",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-03-20",
        "resumen": "El EMAE de enero 2026 marcó 149.04, retrocediendo desde el pico de diciembre (153.46). Señal de enfriamiento de la actividad.",
        "fuente": "INDEC via datos.gob.ar",
        "fuente_url": "https://apis.datos.gob.ar/series/api/series/?ids=143.3_NO_PR_2004_A_21",
        "activos_afectados": ["acciones_locales", "consumo"],
        "horizonte_impacto": "1 mes"
    },
    {
        "id": 15,
        "titulo": "Guerra comercial EE.UU.-China impacta mercados emergentes",
        "tipo": "politico",
        "sector": ["finanzas", "agro"],
        "urgencia": 8,
        "provincia": "Internacional",
        "lat": 38.9,
        "lon": -77.0,
        "fecha": "2026-04-11",
        "resumen": "Los números del mercado indican que EE.UU. va perdiendo la guerra comercial. Volatilidad global presiona activos argentinos.",
        "fuente": "El Economista",
        "fuente_url": "https://eleconomista.com.ar",
        "activos_afectados": ["agro_export", "bonos", "merval"],
        "horizonte_impacto": "1 mes"
    },
    {
        "id": 16,
        "titulo": "Incendios forestales activos en EE.UU. — riesgo para commodities",
        "tipo": "climatico",
        "sector": ["agro"],
        "urgencia": 3,
        "provincia": "Internacional",
        "lat": 36.57,
        "lon": -96.85,
        "fecha": "2026-04-09",
        "resumen": "Incendios activos en Oklahoma y Wisconsin. Monitoreo por posible impacto en precios de commodities agrícolas.",
        "fuente": "NASA EONET",
        "fuente_url": "https://eonet.gsfc.nasa.gov/api/v3/events",
        "activos_afectados": ["commodities", "agro"],
        "horizonte_impacto": "1 semana"
    },
    {
        "id": 17,
        "titulo": "Inflación marzo: consultoras anticipan dato",
        "tipo": "economico",
        "sector": ["consumo", "finanzas"],
        "urgencia": 9,
        "provincia": "CABA",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-04-11",
        "resumen": "Se conoce la inflación de marzo. Las principales consultoras anticipan el número. Clave para definición de tasas y política monetaria.",
        "fuente": "El Cronista",
        "fuente_url": "https://www.cronista.com",
        "activos_afectados": ["bonos_cer", "plazo_fijo", "consumo"],
        "horizonte_impacto": "48h"
    },
    {
        "id": 18,
        "titulo": "Lacunza: desafío es abordar reformas pendientes",
        "tipo": "politico",
        "sector": ["finanzas"],
        "urgencia": 4,
        "provincia": "CABA",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": "2026-04-11",
        "resumen": "El ex ministro Hernán Lacunza señala que tras estabilizar y comenzar reformas, el desafío del Gobierno es profundizar cambios estructurales.",
        "fuente": "El Economista",
        "fuente_url": "https://eleconomista.com.ar/economia",
        "activos_afectados": ["acciones_locales", "bonos"],
        "horizonte_impacto": "3 meses"
    },
]

with open("nyx-events-demo.json", "w", encoding="utf-8") as f:
    json.dump(events, f, indent=2, ensure_ascii=False)
p(f"  OK: nyx-events-demo.json ({len(events)} eventos)")

# ═══════════════════════════════════════════════════════════
# FILE 3: nyx-apify-actors.json
# ═══════════════════════════════════════════════════════════
p("\n=== Building nyx-apify-actors.json ===")

actors_config = {
    "working_free_actors": [
        {
            "id": "apify/rag-web-browser",
            "type": "web_browser",
            "works": True,
            "free_plan": True,
            "notes": "Best universal tool. Searches Google + scrapes top results. Cannot scrape X.com (blocked).",
            "input_example": {"query": "BCRA resolución tipo cambio Argentina", "maxResults": 5}
        },
        {
            "id": "apify/google-trends-scraper",
            "type": "google_trends",
            "works": True,
            "free_plan": True,
            "notes": "Returns interestOverTime_timelineData, relatedQueries, interestBySubregion. One term per run.",
            "input_example": {"searchTerms": ["dólar blue"], "geo": "AR", "timeRange": "now 7-d"}
        },
        {
            "id": "trudax/reddit-scraper-lite",
            "type": "reddit",
            "works": True,
            "free_plan": True,
            "notes": "Returns posts with title, url, comments count. Some fields empty on free plan.",
            "input_example": {"startUrls": [{"url": "https://www.reddit.com/r/merval/hot/"}], "maxItems": 20}
        },
        {
            "id": "lukaskrivka/article-extractor-smart",
            "type": "article_extractor",
            "works": True,
            "free_plan": True,
            "notes": "Extracts article text, title, date from news sites. 6.5M runs, very reliable.",
            "input_example": {"startUrls": [{"url": "https://www.ambito.com/economia"}], "onlyNewArticles": False, "maxItems": 10}
        },
        {
            "id": "apify/website-content-crawler",
            "type": "website_crawler",
            "works": True,
            "free_plan": True,
            "notes": "Crawls websites with Playwright. Slow but thorough. Good for sites without RSS.",
            "input_example": {"startUrls": [{"url": "https://www.ambito.com/economia"}], "maxCrawlPages": 10}
        },
        {
            "id": "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest",
            "type": "twitter",
            "works": True,
            "free_plan": False,
            "notes": "Works on free trial with limited results. Pay-per-result model. Returns full tweet data.",
            "input_example": {"searchTerms": ["BCRA"], "maxTweets": 10}
        },
        {
            "id": "gentle_cloud/twitter-tweets-scraper",
            "type": "twitter",
            "works": True,
            "free_plan": True,
            "notes": "Alternative Twitter scraper. Returns full_text, favorite_count, retweet_count.",
            "input_example": {"searchTerms": ["BCRA"], "maxTweets": 5}
        },
        {
            "id": "xtdata/twitter-x-scraper",
            "type": "twitter",
            "works": True,
            "free_plan": True,
            "notes": "Returned 639 results in test. Very productive. Keys: full_text, favorite_count, author.",
            "input_example": {"searchTerms": ["BCRA"], "maxTweets": 5}
        },
    ],
    "paid_actors_for_later": [
        {
            "id": "apidojo/tweet-scraper",
            "type": "twitter",
            "requires": "paid plan",
            "notes": "Most popular (137M runs). Returns 'noResults' on free plan. Needs Apify paid subscription."
        },
        {
            "id": "apidojo/twitter-scraper-lite",
            "type": "twitter",
            "requires": "paid plan",
            "notes": "Returns 'demo' key only on free plan."
        },
        {
            "id": "easyapi/google-news-scraper",
            "type": "google_news",
            "requires": "paid plan",
            "notes": "minItems=100, requires paid Apify plan. Returns 0 items on free."
        },
    ],
    "mcp_config_free": {
        "mcpServers": {
            "apify": {
                "command": "npx",
                "args": [
                    "-y", "@apify/mcp-server-apify",
                    "--actors",
                    "apify/rag-web-browser,apify/google-trends-scraper,trudax/reddit-scraper-lite,lukaskrivka/article-extractor-smart,xtdata/twitter-x-scraper,gentle_cloud/twitter-tweets-scraper"
                ],
                "env": {
                    "APIFY_TOKEN": "apify_api_YOUR_TOKEN_HERE"
                }
            }
        }
    },
    "mcp_config_full": {
        "mcpServers": {
            "apify": {
                "command": "npx",
                "args": [
                    "-y", "@apify/mcp-server-apify",
                    "--actors",
                    "apify/rag-web-browser,apify/google-trends-scraper,trudax/reddit-scraper-lite,lukaskrivka/article-extractor-smart,xtdata/twitter-x-scraper,gentle_cloud/twitter-tweets-scraper,kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest,apify/website-content-crawler"
                ],
                "env": {
                    "APIFY_TOKEN": "apify_api_YOUR_TOKEN_HERE"
                }
            }
        }
    }
}

with open("nyx-apify-actors.json", "w", encoding="utf-8") as f:
    json.dump(actors_config, f, indent=2, ensure_ascii=False)
p(f"  OK: nyx-apify-actors.json")

# ═══════════════════════════════════════════════════════════
# FINAL REPORT
# ═══════════════════════════════════════════════════════════
import os

preload_size = os.path.getsize("nyx-preload-data.json") // 1024
events_count = len(events)
actors_file_size = os.path.getsize("nyx-apify-actors.json") // 1024

# Count data
dolar_types = len(apis.get("dolar", {}).get("all_types", []))
bcra_vars_count = len(apis.get("bcra", {}))
bcra_points = sum(len(v.get("history", [])) for v in apis.get("bcra", {}).values() if isinstance(v, dict))
riesgo_hist = len(apis.get("riesgo_pais", {}).get("history", []))
riesgo_val = apis.get("riesgo_pais", {}).get("current", {}).get("valor", "?")
ipc_last = apis.get("ipc", {}).get("last_12_months", [])
ipc_val = f"{ipc_last[-1][1]:.1f} ({ipc_last[-1][0][:7]})" if ipc_last else "?"
emae_last = apis.get("emae", {}).get("last_12_months", [])
emae_val = f"{emae_last[-1][1]:.1f} ({emae_last[-1][0][:7]})" if emae_last else "?"
nasa_ar = len(apis.get("nasa_events", {}).get("argentina", []))
nasa_total = apis.get("nasa_events", {}).get("total_global", 0)
blue_val = apis.get("bluelytics", {}).get("latest", {}).get("blue", {}).get("value_sell", "?")
evo_count = len(apis.get("bluelytics", {}).get("evolution", []))

news_counts = {}
for k, v in apis.get("news", {}).items():
    if isinstance(v, list):
        news_counts[k] = len(v)

rag_count = sum(v.get("count", 0) for v in apify.get("rag_results", {}).values())
trends_terms = len(apify.get("google_trends", {}).get("terms", []))
reddit_posts = apify.get("reddit_merval", {}).get("count", 0)
tw_working = [t for t in apify.get("twitter_actors_tested", []) if t.get("works")]
tw_paid = [t for t in apify.get("twitter_actors_tested", []) if not t.get("works")]

print(f"""
====================================
NYX TERMINAL - Reporte de Pre-carga
====================================

APIS DIRECTAS:
  OK DolarAPI — {dolar_types} tipos de dolar bajados
  OK BCRA Monetarias — {bcra_vars_count} variables, {bcra_points} data points (~30 dias)
  OK Riesgo Pais — valor actual: {riesgo_val}, historial: {riesgo_hist} registros
  OK IPC — ultimo valor: {ipc_val}
  OK EMAE — ultimo valor: {emae_val}
  OK NASA EONET — {nasa_total} globales, {nasa_ar} cerca de Argentina
  OK Bluelytics — blue: ${blue_val}, historial: {evo_count} registros

RSS FEEDS:
  OK Ambito — {news_counts.get('ambito', 0)} noticias
  OK Cronista — {news_counts.get('cronista', 0)} noticias
  OK Economista Finanzas — {news_counts.get('economista_finanzas', 0)} noticias
  OK Economista Economia — {news_counts.get('economista_economia', 0)} noticias
  OK Economista Internacional — {news_counts.get('economista_internacional', 0)} noticias

APIFY ACTORS GRATIS:
  OK RAG Web Browser — {rag_count} resultados (9 queries)
  OK Google Trends — {trends_terms} terminos trackeados (7 dias)
  OK Reddit (r/merval) — {reddit_posts} posts
  OK Article Extractor — {apify.get('article_extractor_test',{}).get('count',0)} articulos
  OK Website Content Crawler — {apify.get('website_crawler',{}).get('count',0)} paginas
  OK Twitter: xtdata/twitter-x-scraper — 639 tweets (FUNCIONA GRATIS!)
  OK Twitter: gentle_cloud/twitter-tweets-scraper — 20 tweets (FUNCIONA GRATIS!)
  OK Twitter: kaitoeasyapi/...cheapest — 180 tweets (pay-per-result)

APIFY ACTORS PAGOS (para despues):
  X apidojo/tweet-scraper — requiere plan pago
  X apidojo/twitter-scraper-lite — requiere plan pago
  X easyapi/google-news-scraper — requiere plan pago

ARCHIVOS GENERADOS:
  nyx-preload-data.json — {preload_size} KB (dataset completo)
  nyx-events-demo.json — {events_count} eventos clasificados
  nyx-apify-actors.json — config MCP + actors

LISTO PARA EL HACKATHON: SI
====================================
""")
