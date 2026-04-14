"""Nyx Terminal - Bloque 1: Test de APIs directas"""
import httpx
import json
from datetime import date, timedelta

TIMEOUT = 30
ALL_RESULTS = {}

def api(name, url, method="GET", headers=None, json_body=None):
    try:
        with httpx.Client(timeout=TIMEOUT, verify=False, follow_redirects=True) as c:
            r = c.get(url, headers=headers) if method == "GET" else c.post(url, headers=headers, json=json_body)
            try:
                return r.status_code, r.json(), None
            except:
                return r.status_code, r.text[:300], "Not JSON"
    except Exception as e:
        return None, None, str(e)

def p(msg): print(msg)

H = {"Accept": "application/json"}

# ── DOLAR ──
p("\n=== DOLAR ===")
for tag, url in [("dolares_todos", "https://dolarapi.com/v1/dolares"), ("dolar_blue", "https://dolarapi.com/v1/dolares/blue")]:
    st, d, err = api(tag, url)
    if err:
        p(f"  X {tag}: {err}")
        ALL_RESULTS[tag] = {"status": "FAIL", "error": err}
    else:
        p(f"  OK {tag}: HTTP {st}")
        if isinstance(d, list):
            for x in d:
                p(f"     {x.get('nombre','?')}: compra={x.get('compra')} venta={x.get('venta')}")
            ALL_RESULTS[tag] = {"status": "OK", "http": st, "data": d}
        else:
            p(f"     {d}")
            ALL_RESULTS[tag] = {"status": "OK", "http": st, "data": d}

# ── BCRA MONETARIAS ──
p("\n=== BCRA MONETARIAS ===")
st, d, err = api("bcra_lista", "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias", headers=H)
if err:
    p(f"  X Lista: {err}")
    ALL_RESULTS["bcra_monetarias_lista"] = {"status": "FAIL", "error": err}
else:
    results = d.get("results", d) if isinstance(d, dict) else d
    if isinstance(results, list):
        p(f"  OK Lista: {len(results)} variables. Principales:")
        important_ids = [1, 4, 5, 7, 8, 11, 12, 13, 14, 15]
        for v in results:
            vid = v.get("idVariable", v.get("id"))
            if vid in important_ids:
                p(f"     ID {vid}: {v.get('descripcion', v.get('description','?'))}")
        ALL_RESULTS["bcra_monetarias_lista"] = {"status": "OK", "total_vars": len(results)}

bcra_vars = [
    (1, "Reservas internacionales"),
    (15, "Base monetaria"),
    (7, "Tasa BADLAR"),
    (8, "Tasa TM20"),
    (12, "Tasa depositos 30d"),
    (4, "TC minorista"),
    (5, "TC mayorista"),
]
for vid, vname in bcra_vars:
    url = f"https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{vid}?limit=3"
    st, d, err = api(f"bcra_{vid}", url, headers=H)
    key = f"bcra_var_{vid}"
    if err:
        p(f"  X Var {vid} ({vname}): {err}")
        ALL_RESULTS[key] = {"status": "FAIL", "error": err}
    else:
        res = d.get("results", d) if isinstance(d, dict) else d
        p(f"  OK Var {vid} ({vname}): HTTP {st}")
        if isinstance(res, dict) and "detalle" in res:
            for x in res["detalle"]:
                p(f"     {x.get('fecha')}: {x.get('valor')}")
            ALL_RESULTS[key] = {"status": "OK", "name": vname, "data": res["detalle"]}
        elif isinstance(res, list):
            for x in res[:3]:
                p(f"     {x}")
            ALL_RESULTS[key] = {"status": "OK", "name": vname, "data": res[:3]}
        else:
            p(f"     {str(res)[:200]}")
            ALL_RESULTS[key] = {"status": "OK", "name": vname, "data": str(res)[:200]}

# ── BCRA CAMBIARIAS ──
p("\n=== BCRA CAMBIARIAS ===")
found = False
for days_back in range(0, 7):
    fecha = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = f"https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones?fecha={fecha}"
    st, d, err = api("cambiarias", url, headers=H)
    if err:
        p(f"  X {fecha}: {err}")
        continue
    if st == 200 and d:
        res = d.get("results", d) if isinstance(d, dict) else d
        detalle = res.get("detalle", []) if isinstance(res, dict) else []
        if detalle:
            p(f"  OK Cambiarias fecha={fecha}: {len(detalle)} monedas")
            for c in detalle[:5]:
                p(f"     {c.get('codigoMoneda','?')} ({c.get('descripcion','?')}): {c.get('tipoCotizacion','?')}")
            ALL_RESULTS["bcra_cambiarias"] = {"status": "OK", "fecha": fecha, "monedas": len(detalle), "data": detalle[:10]}
            found = True
            break
        else:
            p(f"  -- {fecha}: 0 monedas, probando anterior...")
if not found:
    ALL_RESULTS["bcra_cambiarias"] = {"status": "FAIL", "note": "Sin datos ultimos 7 dias"}
    p("  X Sin datos en los ultimos 7 dias")

# ── RIESGO PAIS ──
p("\n=== RIESGO PAIS ===")
st, d, err = api("riesgo", "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo")
if err:
    p(f"  X Riesgo pais: {err}")
    ALL_RESULTS["riesgo_pais"] = {"status": "FAIL", "error": err}
else:
    p(f"  OK Riesgo pais: HTTP {st} -> {d}")
    ALL_RESULTS["riesgo_pais"] = {"status": "OK", "data": d}

# ── SERIES TEMPORALES ──
p("\n=== SERIES TEMPORALES ===")
series = [
    ("IPC", "103.1_I2N_2016_M_15"),
    ("EMAE", "143.3_NO_PR_2004_A_21"),
]
for sname, sid in series:
    url = f"https://apis.datos.gob.ar/series/api/series/?ids={sid}&last=5&format=json"
    st, d, err = api(sname, url)
    key = f"serie_{sname.lower()}"
    if err:
        p(f"  X {sname}: {err}")
        ALL_RESULTS[key] = {"status": "FAIL", "error": err}
    elif st == 200 and isinstance(d, dict):
        datos = d.get("data", [])
        meta = d.get("meta", [{}])
        field_desc = ""
        if isinstance(meta, list) and len(meta) > 1:
            field_desc = meta[1].get("field", {}).get("description", "")
        p(f"  OK {sname} ({sid}): HTTP {st} - {field_desc}")
        for row in datos:
            p(f"     {row[0]}: {row[1]}")
        ALL_RESULTS[key] = {"status": "OK", "serie_id": sid, "description": field_desc, "data": datos}
    else:
        p(f"  X {sname}: HTTP {st} - {str(d)[:150]}")
        ALL_RESULTS[key] = {"status": "FAIL", "http": st}

# ── NASA EONET ──
p("\n=== NASA EONET ===")
for tag, url in [
    ("eonet_open", "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=5"),
    ("eonet_fires", "https://eonet.gsfc.nasa.gov/api/v3/events?category=wildfires&status=open&limit=3"),
]:
    st, d, err = api(tag, url)
    if err:
        p(f"  X {tag}: {err}")
        ALL_RESULTS[tag] = {"status": "FAIL", "error": err}
    elif st == 200:
        events = d.get("events", []) if isinstance(d, dict) else []
        p(f"  OK {tag}: {len(events)} eventos")
        for e in events:
            title = e.get("title", "?")
            cats = [c.get("title") for c in e.get("categories", [])]
            geo = e.get("geometry", [{}])
            coords = geo[-1].get("coordinates", "?") if geo else "?"
            gdate = geo[-1].get("date", "?") if geo else "?"
            p(f"     {title} | {cats} | coords={coords} | {gdate}")
        ALL_RESULTS[tag] = {"status": "OK", "count": len(events), "events": [
            {"title": e.get("title"), "categories": [c.get("title") for c in e.get("categories",[])],
             "coords": e.get("geometry",[-1])[-1].get("coordinates") if e.get("geometry") else None,
             "date": e.get("geometry",[-1])[-1].get("date") if e.get("geometry") else None}
            for e in events
        ]}
    else:
        p(f"  X {tag}: HTTP {st}")
        ALL_RESULTS[tag] = {"status": "FAIL", "http": st}

# ── BLUELYTICS ──
p("\n=== BLUELYTICS ===")
st, d, err = api("bluelytics", "https://api.bluelytics.com.ar/v2/latest")
if err:
    p(f"  X Bluelytics: {err}")
    ALL_RESULTS["bluelytics"] = {"status": "FAIL", "error": err}
else:
    p(f"  OK Bluelytics: HTTP {st}")
    if isinstance(d, dict):
        for k, v in d.items():
            p(f"     {k}: {v}")
    ALL_RESULTS["bluelytics"] = {"status": "OK", "data": d}

# Save
with open("test_bloque1_results.json", "w", encoding="utf-8") as f:
    json.dump(ALL_RESULTS, f, indent=2, ensure_ascii=False, default=str)
p("\n>> Guardado en test_bloque1_results.json")
