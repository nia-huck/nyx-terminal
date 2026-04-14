"""Nyx Terminal — Bajada completa de APIs directas (actualizado)"""
import httpx
import feedparser
import json
from datetime import date, timedelta, datetime
import os

TIMEOUT = 30
H = {"Accept": "application/json"}
BASE = "info"

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

def save(path, data):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    size = os.path.getsize(full)
    print(f"  >> {full} ({size//1024}KB)")

def p(msg): print(msg)

# ═══════════════════════════════════════
# DOLAR — todos los tipos + historico
# ═══════════════════════════════════════
p("=== DOLAR ===")
st, d, _ = api("https://dolarapi.com/v1/dolares")
if st == 200:
    p(f"  OK: {len(d)} tipos")
    save("apis/dolar_todos.json", {"fetched_at": datetime.now().isoformat(), "tipos": d})
    for item in d:
        p(f"    {item['nombre']}: compra={item.get('compra')} venta={item.get('venta')}")

st, d, _ = api("https://dolarapi.com/v1/dolares/blue")
if st == 200:
    save("apis/dolar_blue_current.json", d)

# Cotizaciones de todas las monedas
for moneda in ["euro", "real", "chileno", "uruguayo"]:
    st, d, _ = api(f"https://dolarapi.com/v1/cotizaciones/{moneda}")
    if st == 200:
        save(f"apis/cotizacion_{moneda}.json", d)
        p(f"  OK {moneda}: {d}")

# Historico dolar de argentinadatos (30+ dias)
dolar_tipos_hist = ["blue", "oficial", "bolsa", "contadoconliqui", "mayorista", "cripto", "tarjeta"]
for dtipo in dolar_tipos_hist:
    st, d, err = api(f"https://api.argentinadatos.com/v1/cotizaciones/dolares/{dtipo}")
    if st == 200 and isinstance(d, list):
        save(f"apis/dolar_historial_{dtipo}.json", d[-90:])  # 90 dias
        p(f"  OK dolar {dtipo} historial: {len(d)} total, guardados {len(d[-90:])}")
    else:
        p(f"  X dolar {dtipo} historial: {err or f'HTTP {st}'}")

# Bluelytics historico completo
st, d, _ = api("https://api.bluelytics.com.ar/v2/latest")
if st == 200:
    save("apis/bluelytics_latest.json", d)

st, d, _ = api("https://api.bluelytics.com.ar/v2/evolution.json")
if st == 200 and isinstance(d, list):
    save("apis/bluelytics_evolution.json", d[-90:])  # 90 dias
    p(f"  OK bluelytics evolution: {len(d)} total, guardados 90 dias")

# ═══════════════════════════════════════
# BCRA — todas las variables importantes
# ═══════════════════════════════════════
p("\n=== BCRA MONETARIAS ===")

# Lista completa de variables
st, d, _ = api("https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias", headers=H)
if st == 200:
    results = d.get("results", d)
    if isinstance(results, list):
        save("apis/bcra_variables_lista.json", results)
        p(f"  OK lista: {len(results)} variables")

# Variables con historial largo (60 dias)
bcra_vars = {
    1: "reservas_internacionales",
    4: "tc_minorista",
    5: "tc_mayorista",
    6: "tc_promedio",
    7: "tasa_badlar",
    8: "tasa_tm20",
    11: "tasa_baibar",
    12: "tasa_depositos_30d",
    13: "tasa_adelantos_ctacte",
    14: "tasa_prestamos_personales",
    15: "base_monetaria",
    16: "circulacion_monetaria",
    19: "depositos_sector_privado",
    20: "prestamos_sector_privado",
    21: "depositos_sector_publico",
    27: "tasa_pases_activos",
    28: "tasa_pases_pasivos",
    40: "cds_5_anos",
}

bcra_all = {}
for vid, vname in bcra_vars.items():
    url = f"https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{vid}?limit=60"
    st, d, err = api(url, headers=H)
    if err:
        p(f"  X {vname} (ID {vid}): {err}")
        continue
    res = d.get("results", [])
    if isinstance(res, list) and res and isinstance(res[0], dict):
        det = res[0].get("detalle", [])
        p(f"  OK {vname} (ID {vid}): {len(det)} registros")
        bcra_all[vname] = {"id": vid, "data": det}
    else:
        p(f"  ? {vname}: format inesperado")

save("apis/bcra_monetarias_historial.json", {
    "fetched_at": datetime.now().isoformat(),
    "variables": bcra_all
})

# BCRA Cambiarias
p("\n=== BCRA CAMBIARIAS ===")
for days_back in range(0, 7):
    fecha = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    st, d, _ = api(f"https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones?fecha={fecha}", headers=H)
    if st == 200:
        res = d.get("results", {})
        detalle = res.get("detalle", []) if isinstance(res, dict) else []
        if detalle:
            save("apis/bcra_cambiarias.json", {"fecha": fecha, "cotizaciones": detalle})
            p(f"  OK: {len(detalle)} monedas ({fecha})")
            break

# ═══════════════════════════════════════
# RIESGO PAIS — historial completo
# ═══════════════════════════════════════
p("\n=== RIESGO PAIS ===")
st, d, _ = api("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais")
if st == 200 and isinstance(d, list):
    save("apis/riesgo_pais_historial.json", d[-90:])  # 90 dias
    p(f"  OK: {len(d)} total, guardados {len(d[-90:])} ({d[-1]})")

# ═══════════════════════════════════════
# SERIES TEMPORALES — IPC, EMAE y mas
# ═══════════════════════════════════════
p("\n=== SERIES TEMPORALES ===")
series = {
    "ipc_nucleo": "103.1_I2N_2016_M_15",
    "emae": "143.3_NO_PR_2004_A_21",
    "ipc_nacional": "103.1_I2N_2016_M_19",
    "tipo_cambio_nominal": "168.1_T_CAMBIOR_D_0_0_26",
    "merval": "Merval_SL_0_0_37",
    "depositos_plazo_fijo": "61.3_TDEAM_0_M_36",
}
series_data = {}
for sname, sid in series.items():
    url = f"https://apis.datos.gob.ar/series/api/series/?ids={sid}&last=24&format=json"
    st, d, err = api(url)
    if st == 200 and isinstance(d, dict):
        datos = d.get("data", [])
        meta = d.get("meta", [{}])
        desc = ""
        if isinstance(meta, list) and len(meta) > 1:
            desc = meta[1].get("field", {}).get("description", "")
        p(f"  OK {sname}: {len(datos)} periodos — {desc}")
        series_data[sname] = {"serie_id": sid, "description": desc, "data": datos}
    else:
        p(f"  X {sname}: {err or f'HTTP {st}'}")

save("apis/series_temporales.json", {"fetched_at": datetime.now().isoformat(), "series": series_data})

# ═══════════════════════════════════════
# NASA EONET
# ═══════════════════════════════════════
p("\n=== NASA EONET ===")
st, d, _ = api("https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=100")
if st == 200:
    events = d.get("events", [])
    # Filtrar Sudamérica
    latam = []
    for e in events:
        geo = e.get("geometry", [])
        if geo:
            lon, lat = geo[-1].get("coordinates", [0, 0])
            if -56 <= lat <= 15 and -82 <= lon <= -34:
                latam.append(e)
    save("apis/nasa_eonet_all.json", events)
    save("apis/nasa_eonet_latam.json", latam)
    p(f"  OK: {len(events)} global, {len(latam)} LATAM")

# ═══════════════════════════════════════
# ARGENTINA DATOS — mas endpoints
# ═══════════════════════════════════════
p("\n=== ARGENTINA DATOS (extras) ===")
extras = {
    "inflacion_mensual": "https://api.argentinadatos.com/v1/finanzas/indices/inflacion",
    "tasas_plazo_fijo": "https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo",
    "bonos": "https://api.argentinadatos.com/v1/finanzas/bonos",
    "rendimientos": "https://api.argentinadatos.com/v1/finanzas/rendimientos",
}
for ename, eurl in extras.items():
    st, d, err = api(eurl)
    if st == 200 and d:
        if isinstance(d, list):
            save(f"apis/ar_{ename}.json", d[-60:] if len(d) > 60 else d)
            p(f"  OK {ename}: {len(d)} registros")
        else:
            save(f"apis/ar_{ename}.json", d)
            p(f"  OK {ename}")
    else:
        p(f"  X {ename}: {err or f'HTTP {st}'}")

# ═══════════════════════════════════════
# RSS FEEDS
# ═══════════════════════════════════════
p("\n=== RSS FEEDS ===")
feeds = {
    "ambito_economia": "https://www.ambito.com/rss/pages/economia.xml",
    "cronista": "https://www.cronista.com/files/rss/news.xml",
    "economista_finanzas": "https://eleconomista.com.ar/finanzas/feed/",
    "economista_economia": "https://eleconomista.com.ar/economia/feed/",
    "economista_internacional": "https://eleconomista.com.ar/internacional/feed/",
}
all_news = {}
for fname, furl in feeds.items():
    try:
        with httpx.Client(timeout=TIMEOUT, verify=False, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as c:
            r = c.get(furl)
        feed = feedparser.parse(r.text)
        items = []
        for it in feed.entries:
            items.append({
                "titulo": it.get("title", ""),
                "link": it.get("link", ""),
                "fecha": it.get("published", it.get("updated", "")),
                "resumen": it.get("summary", it.get("description", ""))[:500],
            })
        save(f"news/{fname}.json", items)
        all_news[fname] = items
        p(f"  OK {fname}: {len(items)} noticias")
    except Exception as e:
        p(f"  X {fname}: {e}")

save("news/_all_feeds.json", {"fetched_at": datetime.now().isoformat(), "feeds": all_news})
total_news = sum(len(v) for v in all_news.values())
p(f"  TOTAL: {total_news} noticias de {len(all_news)} feeds")

# ═══════════════════════════════════════
# RESUMEN
# ═══════════════════════════════════════
p("\n=== APIs + RSS COMPLETO ===")
total_size = 0
for root, dirs, files in os.walk(BASE):
    for f in files:
        total_size += os.path.getsize(os.path.join(root, f))
p(f"  Total en info/: {total_size//1024} KB")
