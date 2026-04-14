"""Nyx Terminal - Bajada completa de APIs directas + RSS"""
import httpx
import feedparser
import json
from datetime import date, timedelta, datetime

TIMEOUT = 30
H = {"Accept": "application/json"}
DATA = {}

def api(url, headers=None):
    try:
        with httpx.Client(timeout=TIMEOUT, verify=False, follow_redirects=True) as c:
            r = c.get(url, headers=headers)
            try:
                return r.status_code, r.json(), None
            except:
                return r.status_code, r.text[:500], "Not JSON"
    except Exception as e:
        return None, None, str(e)

def p(msg): print(msg)

# ═══════════════════════════════════════
# DOLAR
# ═══════════════════════════════════════
p("=== DOLAR ===")
st, d, err = api("https://dolarapi.com/v1/dolares")
if not err and st == 200:
    current = {}
    for item in d:
        casa = item.get("casa", "")
        current[casa] = item
    p(f"  OK: {len(d)} tipos de dolar")
    DATA["dolar"] = {"current": current, "all_types": d}
else:
    p(f"  X dolares: {err}")
    DATA["dolar"] = {"error": str(err)}

# Intentar historico
for endpoint in ["https://dolarapi.com/v1/dolares/blue/historico",
                  "https://dolarapi.com/v1/ambito/dolares/informal",
                  "https://api.bluelytics.com.ar/v2/evolution.json"]:
    st2, d2, err2 = api(endpoint)
    if not err2 and st2 == 200 and d2:
        if isinstance(d2, list) and len(d2) > 5:
            p(f"  OK historico desde {endpoint}: {len(d2)} registros")
            DATA["dolar"]["history"] = d2[-30:] if len(d2) > 30 else d2
            DATA["dolar"]["history_source"] = endpoint
            break
        elif isinstance(d2, dict):
            p(f"  OK historico desde {endpoint}: dict con keys {list(d2.keys())[:5]}")
            DATA["dolar"]["history"] = d2
            DATA["dolar"]["history_source"] = endpoint
            break
    else:
        p(f"  -- historico {endpoint}: {err2 or f'HTTP {st2}'}")

# ═══════════════════════════════════════
# BCRA MONETARIAS — historial 30 dias
# ═══════════════════════════════════════
p("\n=== BCRA MONETARIAS (historial 30 dias) ===")
bcra_vars = {
    1: "reservas",
    4: "tc_minorista",
    5: "tc_mayorista",
    7: "tasa_badlar",
    8: "tasa_tm20",
    12: "tasa_depositos_30d",
    15: "base_monetaria",
}
DATA["bcra"] = {}
desde = "2026-03-10"
hasta = date.today().strftime("%Y-%m-%d")

for vid, vname in bcra_vars.items():
    url = f"https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{vid}?desde={desde}&hasta={hasta}&limit=100"
    st, d, err = api(url, headers=H)
    if err:
        p(f"  X {vname} (ID {vid}): {err}")
        DATA["bcra"][vname] = {"status": "FAIL", "error": err}
        continue
    res = d.get("results", d) if isinstance(d, dict) else d
    if isinstance(res, dict) and "detalle" in res:
        detalle = res["detalle"]
        current_val = detalle[0] if detalle else None
        p(f"  OK {vname}: {len(detalle)} registros, ultimo={current_val}")
        DATA["bcra"][vname] = {"current": current_val, "history": detalle}
    elif isinstance(res, list):
        p(f"  OK {vname}: {len(res)} registros")
        DATA["bcra"][vname] = {"current": res[0] if res else None, "history": res}
    else:
        p(f"  ? {vname}: {str(res)[:150]}")
        DATA["bcra"][vname] = {"raw": str(res)[:500]}

# ═══════════════════════════════════════
# RIESGO PAIS — historial
# ═══════════════════════════════════════
p("\n=== RIESGO PAIS ===")
st, d, err = api("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais")
if not err and st == 200:
    if isinstance(d, list):
        p(f"  OK: {len(d)} registros totales, ultimos 30 guardados")
        DATA["riesgo_pais"] = {"current": d[-1] if d else None, "history": d[-30:]}
    else:
        p(f"  OK: {d}")
        DATA["riesgo_pais"] = {"current": d}
else:
    # Fallback al ultimo
    st2, d2, _ = api("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo")
    p(f"  Fallback ultimo: {d2}")
    DATA["riesgo_pais"] = {"current": d2}

# ═══════════════════════════════════════
# IPC y EMAE — 12 meses
# ═══════════════════════════════════════
p("\n=== SERIES TEMPORALES ===")
series = [("ipc", "103.1_I2N_2016_M_15"), ("emae", "143.3_NO_PR_2004_A_21")]
for sname, sid in series:
    url = f"https://apis.datos.gob.ar/series/api/series/?ids={sid}&last=12&format=json"
    st, d, err = api(url)
    if not err and st == 200 and isinstance(d, dict):
        datos = d.get("data", [])
        meta = d.get("meta", [{}])
        desc = ""
        if isinstance(meta, list) and len(meta) > 1:
            desc = meta[1].get("field", {}).get("description", "")
        p(f"  OK {sname}: {len(datos)} meses, desc={desc}")
        DATA[sname] = {"last_12_months": datos, "serie_id": sid, "description": desc}
    else:
        p(f"  X {sname}: {err or f'HTTP {st}'}")
        DATA[sname] = {"error": str(err or st)}

# ═══════════════════════════════════════
# NASA EONET — filtrado Argentina
# ═══════════════════════════════════════
p("\n=== NASA EONET ===")
st, d, err = api("https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=50")
if not err and st == 200:
    events = d.get("events", [])
    p(f"  OK: {len(events)} eventos globales")
    # Filtrar cerca de Argentina: lat -22 a -55, lon -73 a -53
    ar_events = []
    for e in events:
        geo = e.get("geometry", [])
        if geo:
            coords = geo[-1].get("coordinates", [0, 0])
            lon, lat = coords[0], coords[1]
            if -55 <= lat <= -22 and -73 <= lon <= -53:
                ar_events.append(e)
    p(f"  Cerca de Argentina: {len(ar_events)} eventos")
    DATA["nasa_events"] = {"total_global": len(events), "argentina": ar_events, "all_events": events[:20]}
else:
    p(f"  X EONET: {err}")
    DATA["nasa_events"] = {"error": str(err)}

# ═══════════════════════════════════════
# BLUELYTICS
# ═══════════════════════════════════════
p("\n=== BLUELYTICS ===")
st, d, err = api("https://api.bluelytics.com.ar/v2/latest")
if not err and st == 200:
    p(f"  OK latest: {d}")
    DATA["bluelytics"] = {"latest": d}
else:
    DATA["bluelytics"] = {"error": str(err)}

st2, d2, err2 = api("https://api.bluelytics.com.ar/v2/evolution.json")
if not err2 and st2 == 200:
    if isinstance(d2, list):
        p(f"  OK evolution: {len(d2)} registros")
        DATA["bluelytics"]["evolution"] = d2[-60:]  # ultimos 60
    else:
        DATA["bluelytics"]["evolution"] = d2
else:
    p(f"  -- evolution: {err2 or f'HTTP {st2}'}")

# ═══════════════════════════════════════
# RSS FEEDS
# ═══════════════════════════════════════
p("\n=== RSS FEEDS ===")
feeds = {
    "ambito": "https://www.ambito.com/rss/pages/economia.xml",
    "cronista": "https://www.cronista.com/files/rss/news.xml",
    "economista_finanzas": "https://eleconomista.com.ar/finanzas/feed/",
    "economista_economia": "https://eleconomista.com.ar/economia/feed/",
    "economista_internacional": "https://eleconomista.com.ar/internacional/feed/",
}
DATA["news"] = {}
for fname, furl in feeds.items():
    try:
        with httpx.Client(timeout=TIMEOUT, verify=False, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}) as c:
            r = c.get(furl)
        feed = feedparser.parse(r.text)
        items = feed.entries
        parsed = []
        for it in items:
            parsed.append({
                "titulo": it.get("title", ""),
                "link": it.get("link", ""),
                "fecha": it.get("published", it.get("updated", "")),
                "resumen": it.get("summary", it.get("description", ""))[:300],
            })
        p(f"  OK {fname}: {len(parsed)} noticias")
        DATA["news"][fname] = parsed
    except Exception as e:
        p(f"  X {fname}: {e}")
        DATA["news"][fname] = {"error": str(e)}

# ═══════════════════════════════════════
# BCRA CAMBIARIAS — ultimo dia habil
# ═══════════════════════════════════════
p("\n=== BCRA CAMBIARIAS ===")
for days_back in range(0, 7):
    fecha = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    st, d, err = api(f"https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones?fecha={fecha}", headers=H)
    if not err and st == 200:
        res = d.get("results", d) if isinstance(d, dict) else d
        detalle = res.get("detalle", []) if isinstance(res, dict) else []
        if detalle:
            p(f"  OK fecha={fecha}: {len(detalle)} monedas")
            DATA["bcra_cambiarias"] = {"fecha": fecha, "cotizaciones": detalle}
            break

# SAVE
p("\n=== GUARDANDO ===")
DATA["generated_at"] = datetime.now().isoformat()
with open("download_apis_results.json", "w", encoding="utf-8") as f:
    json.dump(DATA, f, indent=2, ensure_ascii=False, default=str)
p(f"OK: download_apis_results.json ({len(json.dumps(DATA, default=str))//1024} KB)")
