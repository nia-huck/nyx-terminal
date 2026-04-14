"""Build demo-data.js from nyx-preload-data.json for GitHub Pages."""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE, "data", "nyx-preload-data.json"), encoding="utf-8") as f:
    d = json.load(f)

demo = {}

# ── Dolar ──────────────────────────────────────────────
demo["/dolar"] = d["dolar"]["all_types"]
demo["/dolar/blue"] = d["dolar"]["current"].get("blue", {})

# ── Riesgo pais ────────────────────────────────────────
rp_current = d["riesgo_pais"]["current"]  # {"valor": 557, "fecha": "..."}
demo["/riesgo-pais"] = rp_current
rp_hist = d["riesgo_pais"].get("history", [])
demo["/riesgo-pais/historial?dias=90"] = rp_hist

# ── Inflacion (monthly % from index) ──────────────────
ipc_series = d["ipc"]["last_12_months"]  # [[date, index_value], ...]
inflacion_mensual = []
for i in range(1, len(ipc_series)):
    prev = ipc_series[i - 1]
    curr = ipc_series[i]
    prev_val = prev[1] if isinstance(prev, list) else prev.get("valor", 0)
    curr_val = curr[1] if isinstance(curr, list) else curr.get("valor", 0)
    fecha = curr[0] if isinstance(curr, list) else curr.get("fecha", "")
    if prev_val > 0:
        pct = round((curr_val - prev_val) / prev_val * 100, 1)
        inflacion_mensual.append({"fecha": fecha, "valor": pct})
demo["/inflacion?meses=12"] = inflacion_mensual[-12:]

# ── Reservas ───────────────────────────────────────────
# bcra.reservas = {current: {fecha, valor}, history: [...]}
reservas_data = d["bcra"].get("reservas", {})
if isinstance(reservas_data, dict) and "current" in reservas_data:
    demo["/reservas"] = reservas_data["current"]  # {valor: 44759, fecha: "..."}
else:
    demo["/reservas"] = reservas_data

# ── BADLAR ─────────────────────────────────────────────
badlar_data = d["bcra"].get("tasa_badlar", {})
if isinstance(badlar_data, dict) and "current" in badlar_data:
    badlar_v = badlar_data["current"].get("valor", 23.25)
    badlar_hist = badlar_data.get("history", [])
else:
    badlar_v = badlar_data.get("valor", 23.25) if isinstance(badlar_data, dict) else 23.25
    badlar_hist = []

# BADLAR endpoint — frontend expects array or {valor: ...}
demo["/bcra/badlar"] = badlar_hist if badlar_hist else {"valor": badlar_v}

# ── Signals ────────────────────────────────────────────
blue_v = d["dolar"]["current"].get("blue", {}).get("venta", 1390)
of_v = d["dolar"]["current"].get("oficial", {}).get("venta", 1395)
brecha_pct = round((blue_v - of_v) / of_v * 100, 2) if of_v else 0

# Annualized inflation from monthly % changes
inf_12m = sum(m["valor"] for m in inflacion_mensual[-12:]) if inflacion_mensual else 28.8

demo["/signals"] = {
    "brecha_cambiaria": {"brecha_pct": brecha_pct, "blue": blue_v, "oficial": of_v},
    "tasa_real": {
        "badlar": badlar_v,
        "inflacion_12m": round(inf_12m, 1),
        "tasa_real": round(badlar_v - inf_12m, 1),
    },
    "presion_cambiaria": {"score": 42, "nivel": "moderado"},
    "tendencia_reservas": {"tendencia": "estable", "cambio_pct": -1.2, "dias": 30},
}

# ── Dolar historial (synthetic from current + small variations) ─────
# The bluelytics evolution in preload only has ancient 2011 data ($4),
# so we generate realistic 90-day history from current values.
import random
from datetime import datetime, timedelta

random.seed(42)  # deterministic

blue_now = d["dolar"]["current"].get("blue", {}).get("venta", 1390)
of_now = d["dolar"]["current"].get("oficial", {}).get("venta", 1395)
mep_now = d["dolar"]["current"].get("bolsa", {}).get("venta", 1415)

def gen_history(current_val, days, volatility=0.008):
    """Generate plausible history working backwards from current value."""
    vals = [current_val]
    for _ in range(days - 1):
        change = random.gauss(0.001, volatility)  # slight upward drift
        vals.append(round(vals[-1] / (1 + change), 1))
    vals.reverse()
    return vals

today = datetime(2026, 4, 14)
dates_90 = [(today - timedelta(days=90 - i)).strftime("%Y-%m-%d") for i in range(90)]

blue_vals = gen_history(blue_now, 90, 0.006)
of_vals = gen_history(of_now, 90, 0.003)
mep_vals = gen_history(mep_now, 90, 0.005)

demo["/dolar/historial/blue?dias=90"] = [
    {"fecha": dates_90[i], "venta": blue_vals[i], "compra": round(blue_vals[i] - 15, 1)}
    for i in range(90)
]
demo["/dolar/historial/oficial?dias=90"] = [
    {"fecha": dates_90[i], "venta": of_vals[i], "compra": round(of_vals[i] - 50, 1)}
    for i in range(90)
]
demo["/dolar/historial/bolsa?dias=90"] = [
    {"fecha": dates_90[i], "venta": mep_vals[i], "compra": round(mep_vals[i] - 7, 1)}
    for i in range(90)
]

# ── Eventos ────────────────────────────────────────────
news_all = []
for source, articles in d.get("news", {}).items():
    if isinstance(articles, list):
        for a in articles:
            a["_source"] = source
        news_all.extend(articles)

# Province coordinates for realistic geo spread
prov_coords = [
    (-34.6, -58.4), (-31.4, -64.2), (-32.9, -60.7), (-34.9, -57.9),
    (-26.8, -65.2), (-24.8, -65.4), (-31.5, -68.5), (-33.3, -66.3),
    (-27.5, -59.0), (-38.0, -57.5), (-43.3, -65.3), (-36.6, -64.3),
    (-29.4, -66.8), (-27.4, -55.9), (-38.9, -68.0), (-31.6, -60.7),
]

events = []
tipos = ["economico", "sindical", "regulatorio", "politico", "informativo"]
for i, n in enumerate(news_all[:25]):
    title = n.get("title", n.get("titulo", ""))
    if not title:
        continue
    coord = prov_coords[i % len(prov_coords)]
    events.append({
        "titulo": title,
        "tipo": tipos[i % len(tipos)],
        "urgencia": max(3, min(9, 5 + (i % 5))),
        "sector": "economia",
        "fuente": n.get("_source", ""),
        "lat": coord[0],
        "lng": coord[1],
    })
demo["/eventos"] = events

# ── Indice Nyx ─────────────────────────────────────────
demo["/analisis/indice-nyx"] = {
    "score": 47,
    "nivel": "moderado",
    "alertas": [
        "Brecha cambiaria en rango de convergencia",
        "Reservas BCRA: USD {:.0f}M, tendencia estable".format(
            reservas_data.get("current", {}).get("valor", 44759) if isinstance(reservas_data, dict) else 44759
        ),
        "Tasa real negativa: BADLAR {:.1f}% vs inflacion {:.1f}%".format(badlar_v, inf_12m),
        "Riesgo pais: {} pts, mejorando".format(rp_current.get("valor", 557)),
        "Dolar blue estable en convergencia con oficial",
        "Inflacion mensual: {:.1f}% ultimo mes".format(inflacion_mensual[-1]["valor"] if inflacion_mensual else 2.9),
        "Presion cambiaria moderada, sin senales de estres",
    ],
    "componentes": {"cambiario": 35, "monetario": 40, "fiscal": 50, "externo": 55, "social": 42},
}

# ── Resumen ────────────────────────────────────────────
demo["/analisis/resumen"] = {
    "resumen": "Contexto macroeconomico argentino con brecha cambiaria en convergencia. "
    "Reservas en USD {:.0f}M con tendencia estable. ".format(
        reservas_data.get("current", {}).get("valor", 44759) if isinstance(reservas_data, dict) else 44759
    )
    + "BADLAR en {:.1f}% con tasa real negativa. Riesgo pais en {} pts.".format(badlar_v, rp_current.get("valor", 557)),
    "alertas": demo["/analisis/indice-nyx"]["alertas"],
}

# ── Noticias ───────────────────────────────────────────
noticias = []
for source, articles in d.get("news", {}).items():
    if isinstance(articles, list):
        for a in articles[:8]:
            noticias.append({
                "titulo": a.get("title", a.get("titulo", "")),
                "fuente": source,
                "url": a.get("url", a.get("link", "")),
                "fecha": a.get("date", a.get("fecha", "")),
                "resumen": (a.get("description", a.get("summary", "")) or "")[:200],
            })
demo["/noticias"] = noticias[:30]

# ── Sentiment ──────────────────────────────────────────
tweets = d.get("apify_results", {}).get("twitter_results", [])
demo["/analisis/sentiment"] = {
    "tono": "neutro",
    "positivos": 8,
    "negativos": 12,
    "neutros": 15,
    "total_tweets": max(len(tweets), 35),
    "volumen_por_tema": {"dolar": 15, "inflacion": 12, "reservas": 8, "riesgo_pais": 6, "cepo": 4},
}

# ── Velocidad / Monetario ──────────────────────────────
demo["/analisis/dolar/velocidad"] = {
    "variacion_diaria": 0.3, "variacion_semanal": 1.2, "variacion_mensual": 3.5, "tendencia": "estable",
}

bm_data = d["bcra"].get("base_monetaria", {})
bm_val = bm_data.get("current", {}).get("valor", 41265125) if isinstance(bm_data, dict) and "current" in bm_data else bm_data
demo["/analisis/monetario"] = {
    "base_monetaria": bm_val,
    "expansion_mensual": 2.1,
    "velocidad_emision": "moderada",
}

# ── Social feeds ───────────────────────────────────────
demo["/tweets"] = (tweets or [])[:20]

reddit_raw = d.get("apify_results", {}).get("reddit_merval", [])
if isinstance(reddit_raw, dict):
    reddit_raw = reddit_raw.get("posts", reddit_raw.get("results", []))
demo["/reddit"] = (reddit_raw or [])[:20]

trends_raw = d.get("apify_results", {}).get("google_trends", [])
if isinstance(trends_raw, dict):
    trends_raw = trends_raw.get("terms", trends_raw.get("results", []))
demo["/trends"] = (trends_raw or [])[:20]

# ── Config / Status ────────────────────────────────────
demo["/config"] = {"mode": "analyst", "temperature": 0.3}
demo["/summary"] = {"status": "demo", "sources": list(d.keys()), "generated_at": d["generated_at"]}
demo["/"] = {"status": "ok", "mode": "demo", "version": "1.0.0"}

# ── Write output ───────────────────────────────────────
out_path = os.path.join(BASE, "docs", "demo-data.js")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("/* Nyx Terminal - Demo Data (auto-generated) */\n")
    f.write("window.NYX_DEMO_DATA = ")
    json.dump(demo, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")

size = os.path.getsize(out_path) / 1024
print(f"Generated {out_path}")
print(f"Endpoints: {len(demo)}")
print(f"Size: {size:.1f} KB")

# Verify key values
print(f"\nVerification:")
print(f"  Reservas: {demo['/reservas']}")
print(f"  BADLAR: {badlar_v}%")
print(f"  Inflacion 12m sum: {inf_12m}%")
print(f"  Tasa real: {round(badlar_v - inf_12m, 1)}%")
print(f"  Brecha: {brecha_pct}%")
print(f"  Blue hist points: {len(demo['/dolar/historial/blue?dias=90'])}")
print(f"  Oficial hist points: {len(demo['/dolar/historial/oficial?dias=90'])}")
print(f"  Riesgo pais hist: {len(rp_hist)}")
print(f"  Inflacion meses: {len(inflacion_mensual)}")
print(f"  Eventos: {len(events)}")
