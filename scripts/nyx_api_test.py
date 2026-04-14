"""
Nyx Terminal - API Testing Script
Tests all economic APIs and Apify integration
"""
import httpx
import feedparser
import json
import time
from datetime import datetime, date

RESULTS = {}
TIMEOUT = 30

def log(msg):
    print(f"  {msg}")

def test_api(name, url, method="GET", headers=None, json_body=None, expect_json=True):
    """Generic API tester. Returns (status_code, data_or_text, error)."""
    try:
        with httpx.Client(timeout=TIMEOUT, verify=False, follow_redirects=True) as client:
            if method == "POST":
                r = client.post(url, headers=headers, json=json_body)
            else:
                r = client.get(url, headers=headers)
            if expect_json:
                try:
                    data = r.json()
                    return r.status_code, data, None
                except Exception:
                    return r.status_code, r.text[:500], "Not JSON"
            else:
                return r.status_code, r.text[:500], None
    except Exception as e:
        return None, None, str(e)

# ============================================================
# PARTE 1: APIs Económicas
# ============================================================
print("=" * 70)
print("PARTE 1: TEST DE APIs ECONÓMICAS")
print("=" * 70)

# --- 1. DolarAPI ---
print("\n📌 1. DolarAPI.com")
status, data, err = test_api("DolarAPI - Todos", "https://dolarapi.com/v1/dolares")
if err:
    log(f"❌ /dolares: {err}")
    RESULTS["dolarapi_todos"] = {"status": "FAIL", "error": err}
else:
    log(f"✅ /dolares: HTTP {status}, {len(data)} tipos de dólar")
    if isinstance(data, list) and len(data) > 0:
        log(f"   Campos: {list(data[0].keys())}")
        for d in data[:3]:
            log(f"   {d.get('nombre','?')}: compra={d.get('compra')}, venta={d.get('venta')}")
    RESULTS["dolarapi_todos"] = {"status": "OK", "http": status, "count": len(data) if isinstance(data, list) else "N/A", "sample": data[:2] if isinstance(data, list) else str(data)[:200]}

status, data, err = test_api("DolarAPI - Blue", "https://dolarapi.com/v1/dolares/blue")
if err:
    log(f"❌ /dolares/blue: {err}")
    RESULTS["dolarapi_blue"] = {"status": "FAIL", "error": err}
else:
    log(f"✅ /dolares/blue: HTTP {status}")
    if isinstance(data, dict):
        log(f"   Blue: compra={data.get('compra')}, venta={data.get('venta')}, fecha={data.get('fechaActualizacion')}")
    RESULTS["dolarapi_blue"] = {"status": "OK", "http": status, "data": data if isinstance(data, dict) else str(data)[:200]}

# --- 2. BCRA API v4.0 Monetarias ---
print("\n📌 2. BCRA API v4.0 Monetarias")
bcra_headers = {"Accept": "application/json"}

status, data, err = test_api("BCRA Monetarias lista", "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias", headers=bcra_headers)
if err:
    log(f"❌ Monetarias lista: {err}")
    RESULTS["bcra_monetarias_lista"] = {"status": "FAIL", "error": err}
else:
    log(f"✅ Monetarias lista: HTTP {status}")
    results_data = data.get("results", data) if isinstance(data, dict) else data
    if isinstance(results_data, list):
        log(f"   Total variables: {len(results_data)}")
        for v in results_data[:10]:
            vid = v.get("idVariable", v.get("id", "?"))
            desc = v.get("descripcion", v.get("description", "?"))
            log(f"   ID {vid}: {desc}")
    RESULTS["bcra_monetarias_lista"] = {"status": "OK", "http": status, "sample": str(data)[:500]}

for var_id, var_name in [(1, "Reservas internacionales"), (15, "Base monetaria")]:
    url = f"https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{var_id}?limit=5"
    status, data, err = test_api(f"BCRA {var_name}", url, headers=bcra_headers)
    key = f"bcra_monetarias_{var_id}"
    if err:
        log(f"❌ Variable {var_id} ({var_name}): {err}")
        RESULTS[key] = {"status": "FAIL", "error": err}
    else:
        log(f"✅ Variable {var_id} ({var_name}): HTTP {status}")
        results_data = data.get("results", data) if isinstance(data, dict) else data
        if isinstance(results_data, list) and len(results_data) > 0:
            log(f"   Último: {results_data[-1]}")
        elif isinstance(results_data, dict):
            log(f"   Data: {str(results_data)[:200]}")
        RESULTS[key] = {"status": "OK", "http": status, "sample": str(data)[:300]}

# --- 3. BCRA Estadísticas Cambiarias ---
print("\n📌 3. BCRA Estadísticas Cambiarias")
today = date.today()
# Try today, then yesterday, then day before (weekends)
for days_back in range(0, 5):
    d = date.fromordinal(today.toordinal() - days_back)
    fecha = d.strftime("%Y-%m-%d")
    url = f"https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones?fecha={fecha}"
    status, data, err = test_api(f"BCRA Cambiarias {fecha}", url, headers=bcra_headers)
    if err:
        log(f"  ❌ fecha={fecha}: {err}")
        if days_back == 0:
            RESULTS["bcra_cambiarias"] = {"status": "FAIL", "error": err}
        continue
    if status == 200 and data:
        results_data = data.get("results", data) if isinstance(data, dict) else data
        log(f"✅ Cambiarias fecha={fecha}: HTTP {status}")
        if isinstance(results_data, dict):
            detalle = results_data.get("detalle", [])
            log(f"   Cotizaciones: {len(detalle)} monedas")
            for c in detalle[:3]:
                log(f"   {c.get('codigoMoneda','?')} ({c.get('descripcion','?')}): {c.get('tipoCotizacion','?')}")
        RESULTS["bcra_cambiarias"] = {"status": "OK", "http": status, "fecha": fecha, "sample": str(data)[:400]}
        break
    else:
        log(f"  ⚠️ fecha={fecha}: HTTP {status}")
        if days_back == 4:
            RESULTS["bcra_cambiarias"] = {"status": "FAIL", "http": status, "note": "No data for last 5 days"}

# --- 4. Riesgo País ---
print("\n📌 4. Riesgo País")
riesgo_urls = [
    ("argentinadatos riesgo-pais", "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo"),
    ("argentinadatos riesgoPais", "https://api.argentinadatos.com/v1/finanzas/indices/riesgoPais/ultimo"),
    ("argentinadatos riesgo-pais list", "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais"),
]
riesgo_found = False
for name, url in riesgo_urls:
    status, data, err = test_api(name, url)
    if err:
        log(f"  ❌ {name}: {err}")
    elif status == 200:
        log(f"✅ {name}: HTTP {status}")
        log(f"   Data: {str(data)[:200]}")
        RESULTS["riesgo_pais"] = {"status": "OK", "http": status, "endpoint": url, "sample": str(data)[:300]}
        riesgo_found = True
        break
    else:
        log(f"  ⚠️ {name}: HTTP {status} - {str(data)[:100]}")

if not riesgo_found:
    log("Intentando alternativa con argentinadatos base...")
    status, data, err = test_api("argentinadatos base", "https://api.argentinadatos.com/v1/")
    if not err:
        log(f"   Base endpoint: {str(data)[:300]}")
    RESULTS["riesgo_pais"] = {"status": "FAIL", "note": "Ningún endpoint probado funcionó"}

# --- 5. Series Temporales Argentina ---
print("\n📌 5. Series Temporales Argentina (datos.gob.ar)")
series = [
    ("IPC", "148.3_INIVELGENERAL_DICI_M_26"),
    ("EMAE", "143.3_NO_PR_2004_A_21"),
]
for sname, sid in series:
    url = f"https://apis.datos.gob.ar/series/api/series/?ids={sid}&last=5&format=json"
    status, data, err = test_api(f"Series {sname}", url)
    key = f"series_{sname.lower()}"
    if err:
        log(f"❌ {sname} ({sid}): {err}")
        RESULTS[key] = {"status": "FAIL", "error": err}
    elif status == 200:
        log(f"✅ {sname}: HTTP {status}")
        if isinstance(data, dict) and "data" in data:
            log(f"   Últimos valores: {data['data'][-3:]}")
            meta = data.get("meta", [{}])
            if meta:
                log(f"   Meta: {str(meta[0] if isinstance(meta, list) else meta)[:150]}")
        RESULTS[key] = {"status": "OK", "http": status, "serie_id": sid, "sample": str(data)[:400]}
    else:
        log(f"⚠️ {sname}: HTTP {status}")
        RESULTS[key] = {"status": "FAIL", "http": status}

# --- 6. NASA EONET ---
print("\n📌 6. NASA EONET")
status, data, err = test_api("EONET events", "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=5")
if err:
    log(f"❌ EONET events: {err}")
    RESULTS["nasa_eonet"] = {"status": "FAIL", "error": err}
elif status == 200:
    events = data.get("events", []) if isinstance(data, dict) else []
    log(f"✅ EONET: HTTP {status}, {len(events)} eventos")
    for e in events[:3]:
        title = e.get("title", "?")
        cats = [c.get("title", "?") for c in e.get("categories", [])]
        geo = e.get("geometry", [{}])
        coords = geo[0].get("coordinates", "?") if geo else "?"
        log(f"   {title} | Cat: {cats} | Coords: {coords}")
    RESULTS["nasa_eonet"] = {"status": "OK", "http": status, "events_count": len(events), "sample": str(events[:2])[:400]}
else:
    log(f"⚠️ EONET: HTTP {status}")
    RESULTS["nasa_eonet"] = {"status": "FAIL", "http": status}

status, data, err = test_api("EONET wildfires", "https://eonet.gsfc.nasa.gov/api/v3/events?category=wildfires&status=open&limit=3")
if not err and status == 200:
    events = data.get("events", [])
    log(f"✅ EONET wildfires: {len(events)} incendios activos")
    RESULTS["nasa_eonet_wildfires"] = {"status": "OK", "count": len(events)}
else:
    log(f"⚠️ EONET wildfires: {err or f'HTTP {status}'}")
    RESULTS["nasa_eonet_wildfires"] = {"status": "FAIL"}

# --- 7. RSS Feeds ---
print("\n📌 7. RSS Feeds argentinos")
feeds = [
    ("Ámbito Economía", "https://www.ambito.com/rss/pages/economia.xml"),
    ("El Cronista", "https://www.cronista.com/files/rss/news.xml"),
    ("El Economista", "https://eleconomista.com.ar/finanzas/feed/"),
    ("iProfesional", "https://www.iprofesional.com/rss"),
]
for fname, furl in feeds:
    try:
        with httpx.Client(timeout=TIMEOUT, verify=False, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
            r = client.get(furl)
        feed = feedparser.parse(r.text)
        items = feed.entries
        if items:
            latest = items[0].get("title", "Sin título")
            log(f"✅ {fname}: {len(items)} items | Último: {latest[:80]}")
            RESULTS[f"rss_{fname.lower().replace(' ','_')}"] = {"status": "OK", "items": len(items), "latest": latest[:100]}
        else:
            log(f"⚠️ {fname}: Feed parseado pero 0 items (HTTP {r.status_code})")
            RESULTS[f"rss_{fname.lower().replace(' ','_')}"] = {"status": "PARTIAL", "note": "0 items", "http": r.status_code}
    except Exception as e:
        log(f"❌ {fname}: {e}")
        RESULTS[f"rss_{fname.lower().replace(' ','_')}"] = {"status": "FAIL", "error": str(e)}

# --- 8. Boletín Oficial ---
print("\n📌 8. Boletín Oficial")
status, data, err = test_api(
    "Boletín Oficial",
    "https://www.boletinoficial.gob.ar/norma/detallePrimera",
    method="POST",
    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    json_body={"numeroTramite": "147002"}
)
if err:
    log(f"❌ Boletín Oficial: {err}")
    RESULTS["boletin_oficial"] = {"status": "FAIL", "error": err}
elif status == 200:
    log(f"✅ Boletín Oficial: HTTP {status}")
    if isinstance(data, dict):
        dl = data.get("dataList", [])
        log(f"   dataList: {len(dl)} items")
        if dl:
            first = dl[0] if isinstance(dl, list) else dl
            log(f"   Campos: {list(first.keys()) if isinstance(first, dict) else str(first)[:150]}")
    RESULTS["boletin_oficial"] = {"status": "OK", "http": status, "sample": str(data)[:400]}
else:
    log(f"⚠️ Boletín Oficial: HTTP {status}")
    log(f"   Response: {str(data)[:200]}")
    RESULTS["boletin_oficial"] = {"status": "FAIL", "http": status, "response": str(data)[:200]}

# --- 9. Bluelytics ---
print("\n📌 9. Bluelytics")
status, data, err = test_api("Bluelytics", "https://api.bluelytics.com.ar/v2/latest")
if err:
    log(f"❌ Bluelytics: {err}")
    RESULTS["bluelytics"] = {"status": "FAIL", "error": err}
elif status == 200:
    log(f"✅ Bluelytics: HTTP {status}")
    if isinstance(data, dict):
        for k, v in data.items():
            log(f"   {k}: {v}")
    RESULTS["bluelytics"] = {"status": "OK", "http": status, "data": data if isinstance(data, dict) else str(data)[:300]}
else:
    log(f"⚠️ Bluelytics: HTTP {status}")
    RESULTS["bluelytics"] = {"status": "FAIL", "http": status}


# ============================================================
# PARTE 2: Apify
# ============================================================
print("\n" + "=" * 70)
print("PARTE 2: APIFY TEST")
print("=" * 70)

from apify_client import ApifyClient
APIFY_TOKEN = "apify_api_YOUR_TOKEN_HERE"
apify = ApifyClient(APIFY_TOKEN)

# 2a. Search Store
print("\n📌 2a. Buscar actors en Apify Store")

# Twitter scrapers
print("\n  🔍 Twitter scrapers:")
try:
    store = apify.store()
    twitter_actors = list(store.list(search="twitter scraper", limit=5).items)
    for a in twitter_actors:
        name = a.get("name", "?")
        username = a.get("username", "?")
        runs = a.get("stats", {}).get("totalRuns", "?")
        log(f"   {username}/{name} — runs: {runs}")
    RESULTS["apify_twitter_actors"] = {"status": "OK", "count": len(twitter_actors), "actors": [{"name": a.get("name"), "username": a.get("username"), "runs": a.get("stats",{}).get("totalRuns")} for a in twitter_actors]}
except Exception as e:
    log(f"❌ Twitter search: {e}")
    RESULTS["apify_twitter_actors"] = {"status": "FAIL", "error": str(e)}

# Google News scrapers
print("\n  🔍 Google News scrapers:")
try:
    news_actors = list(store.list(search="google news scraper", limit=3).items)
    for a in news_actors:
        name = a.get("name", "?")
        username = a.get("username", "?")
        runs = a.get("stats", {}).get("totalRuns", "?")
        log(f"   {username}/{name} — runs: {runs}")
    RESULTS["apify_news_actors"] = {"status": "OK", "count": len(news_actors), "actors": [{"name": a.get("name"), "username": a.get("username"), "runs": a.get("stats",{}).get("totalRuns")} for a in news_actors]}
except Exception as e:
    log(f"❌ News search: {e}")
    RESULTS["apify_news_actors"] = {"status": "FAIL", "error": str(e)}

# 2a. Run RAG Web Browser
print("\n📌 2b. Ejecutar apify/rag-web-browser")
try:
    run_input = {
        "query": "BCRA resolución tipo cambio Argentina",
        "maxResults": 3,
    }
    run = apify.actor("apify/rag-web-browser").call(run_input=run_input, timeout_secs=120)
    dataset_items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
    log(f"✅ RAG Web Browser: {len(dataset_items)} resultados")
    for i, item in enumerate(dataset_items):
        title = item.get("title", item.get("metadata", {}).get("title", "?"))
        url = item.get("url", item.get("metadata", {}).get("url", "?"))
        text_preview = str(item.get("text", item.get("markdown", "")))[:150]
        log(f"   [{i+1}] {title}")
        log(f"       URL: {url}")
        log(f"       Preview: {text_preview}...")
    RESULTS["apify_rag_browser"] = {"status": "OK", "results": len(dataset_items), "sample": str(dataset_items[0])[:400] if dataset_items else "empty"}
except Exception as e:
    log(f"❌ RAG Web Browser: {e}")
    RESULTS["apify_rag_browser"] = {"status": "FAIL", "error": str(e)}


# ============================================================
# Save results
# ============================================================
print("\n" + "=" * 70)
print("GUARDANDO RESULTADOS")
print("=" * 70)

with open("nyx-api-test-results.json", "w", encoding="utf-8") as f:
    json.dump(RESULTS, f, indent=2, ensure_ascii=False, default=str)
log("✅ Resultados guardados en nyx-api-test-results.json")

# ============================================================
# PARTE 3: Resumen final
# ============================================================
print("\n" + "=" * 70)
print("PARTE 3: RESUMEN FINAL")
print("=" * 70)

print("\n┌─────────────────────────────────┬────────┬─────────────────────────────────────────┐")
print("│ Fuente                          │ Status │ Notas                                   │")
print("├─────────────────────────────────┼────────┼─────────────────────────────────────────┤")
summary_rows = [
    ("DolarAPI /dolares", "dolarapi_todos"),
    ("DolarAPI /blue", "dolarapi_blue"),
    ("BCRA Monetarias (lista)", "bcra_monetarias_lista"),
    ("BCRA Monetarias/1 (Reservas)", "bcra_monetarias_1"),
    ("BCRA Monetarias/15 (Base Mon.)", "bcra_monetarias_15"),
    ("BCRA Cambiarias", "bcra_cambiarias"),
    ("Riesgo País", "riesgo_pais"),
    ("Series IPC", "series_ipc"),
    ("Series EMAE", "series_emae"),
    ("NASA EONET", "nasa_eonet"),
    ("RSS Ámbito", "rss_ámbito_economía"),
    ("RSS Cronista", "rss_el_cronista"),
    ("RSS El Economista", "rss_el_economista"),
    ("RSS iProfesional", "rss_iprofesional"),
    ("Boletín Oficial", "boletin_oficial"),
    ("Bluelytics", "bluelytics"),
    ("Apify Twitter Actors", "apify_twitter_actors"),
    ("Apify News Actors", "apify_news_actors"),
    ("Apify RAG Browser", "apify_rag_browser"),
]
for label, key in summary_rows:
    r = RESULTS.get(key, {"status": "NOT_RUN"})
    st = r.get("status", "?")
    icon = "✅" if st == "OK" else ("⚠️" if st == "PARTIAL" else "❌")
    note = ""
    if st == "OK":
        if "items" in r:
            note = f"{r['items']} items"
        elif "count" in r:
            note = f"{r['count']} results"
        elif "events_count" in r:
            note = f"{r['events_count']} events"
        elif "endpoint" in r:
            note = r["endpoint"][:40]
    elif "error" in r:
        note = str(r["error"])[:40]
    elif "note" in r:
        note = str(r["note"])[:40]
    print(f"│ {label:<31} │ {icon}  │ {note:<39} │")
print("└─────────────────────────────────┴────────┴─────────────────────────────────────────┘")

print("\n✅ Test completo. Revisá nyx-api-test-results.json para detalles.")
