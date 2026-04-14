"""Build demo-data.js from nyx-preload-data.json for GitHub Pages."""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE, "data", "nyx-preload-data.json"), encoding="utf-8") as f:
    d = json.load(f)

demo = {}

# /dolar
demo["/dolar"] = d["dolar"]["all_types"]
demo["/dolar/blue"] = d["dolar"]["current"].get("blue", {})

# /riesgo-pais
demo["/riesgo-pais"] = d["riesgo_pais"]["current"]
rp_hist = d["riesgo_pais"].get("history", [])
demo["/riesgo-pais/historial?dias=90"] = rp_hist[-90:]

# /inflacion - compute monthly % from index
ipc_series = d["ipc"]["last_12_months"]
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

# /reservas
demo["/reservas"] = d["bcra"].get("reservas", {})

# /signals
blue_v = d["dolar"]["current"].get("blue", {}).get("venta", 1390)
of_v = d["dolar"]["current"].get("oficial", {}).get("venta", 1395)
badlar_raw = d["bcra"].get("tasa_badlar", {})
if isinstance(badlar_raw, dict):
    badlar_v = badlar_raw.get("valor", badlar_raw.get("value", 37))
elif isinstance(badlar_raw, list) and badlar_raw:
    badlar_v = badlar_raw[-1].get("valor", 37)
else:
    badlar_v = 37

ipc_raw = d["ipc"]["last_12_months"]
# IPC can be [[date, value], ...] or [{"fecha":..., "valor":...}, ...]
def ipc_val(item):
    if isinstance(item, list):
        return item[1] if len(item) > 1 else 0
    if isinstance(item, dict):
        return item.get("valor", item.get("value", 0))
    return float(item) if item else 0

# Convert to standard format for frontend
ipc = []
for item in ipc_raw:
    if isinstance(item, list):
        ipc.append({"fecha": item[0], "valor": item[1]})
    else:
        ipc.append(item)
ipc_12m = sum(ipc_val(i) for i in ipc_raw[-12:]) if ipc_raw else 30
brecha_pct = round((blue_v - of_v) / of_v * 100, 2) if of_v else 0

demo["/signals"] = {
    "brecha_cambiaria": {"brecha_pct": brecha_pct, "blue": blue_v, "oficial": of_v},
    "tasa_real": {"badlar": badlar_v, "inflacion_12m": round(ipc_12m, 1), "tasa_real": round(badlar_v - ipc_12m, 1)},
    "presion_cambiaria": {"score": 42, "nivel": "moderado"},
    "tendencia_reservas": {"tendencia": "estable", "cambio_pct": -1.2, "dias": 30},
}

# /eventos
news_all = []
for source, articles in d.get("news", {}).items():
    if isinstance(articles, list):
        for a in articles:
            a["_source"] = source
        news_all.extend(articles)

events = []
tipos = ["economico", "sindical", "regulatorio", "politico", "informativo"]
for i, n in enumerate(news_all[:25]):
    title = n.get("title", n.get("titulo", ""))
    if not title:
        continue
    events.append({
        "titulo": title,
        "tipo": tipos[i % len(tipos)],
        "urgencia": max(3, min(9, 5 + (i % 5))),
        "sector": "economia",
        "fuente": n.get("_source", ""),
        "lat": -34.6 + (i % 10) * 0.8,
        "lng": -58.4 + (i % 8) * 1.2,
    })
demo["/eventos"] = events

# /analisis/indice-nyx
demo["/analisis/indice-nyx"] = {
    "score": 47,
    "nivel": "moderado",
    "alertas": [
        "Brecha cambiaria en rango moderado",
        "Reservas con tendencia estable",
        "Tasa real negativa: rendimientos no cubren inflacion",
    ],
    "componentes": {"cambiario": 45, "monetario": 40, "fiscal": 50, "externo": 55, "social": 42},
}

# /analisis/resumen
demo["/analisis/resumen"] = {
    "resumen": "Contexto macroeconomico argentino con brecha cambiaria moderada. Reservas estables. Tasa real negativa.",
    "alertas": demo["/analisis/indice-nyx"]["alertas"],
}

# /dolar/historial/*
evol = d.get("bluelytics", {}).get("evolution", [])
blue_hist, of_hist = [], []
for e in evol[-90:]:
    date = e.get("date", "")
    if "blue" in e and e["blue"]:
        blue_hist.append({"fecha": date, "venta": e["blue"].get("value_sell", 0), "compra": e["blue"].get("value_buy", 0)})
    if "oficial" in e and e["oficial"]:
        of_hist.append({"fecha": date, "venta": e["oficial"].get("value_sell", 0), "compra": e["oficial"].get("value_buy", 0)})

demo["/dolar/historial/blue?dias=90"] = blue_hist[-90:]
demo["/dolar/historial/oficial?dias=90"] = of_hist[-90:]
demo["/dolar/historial/bolsa?dias=90"] = []

# /bcra/badlar
demo["/bcra/badlar"] = d["bcra"].get("tasa_badlar", {})

# /noticias
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

# /analisis/sentiment
tweets = d.get("apify_results", {}).get("twitter_results", [])
demo["/analisis/sentiment"] = {
    "tono": "neutro",
    "positivos": 8,
    "negativos": 12,
    "neutros": 15,
    "total_tweets": max(len(tweets), 35),
    "volumen_por_tema": {"dolar": 15, "inflacion": 12, "reservas": 8, "riesgo_pais": 6, "cepo": 4},
}

# /analisis/dolar/velocidad
demo["/analisis/dolar/velocidad"] = {"variacion_diaria": 0.3, "variacion_semanal": 1.2, "variacion_mensual": 3.5, "tendencia": "estable"}

# /analisis/monetario
demo["/analisis/monetario"] = {"base_monetaria": d["bcra"].get("base_monetaria", {}), "expansion_mensual": 2.1, "velocidad_emision": "moderada"}

# /tweets, /reddit, /trends
demo["/tweets"] = (d.get("apify_results", {}).get("twitter_results", []))[:20]
reddit_raw = d.get("apify_results", {}).get("reddit_merval", [])
if isinstance(reddit_raw, dict):
    reddit_raw = reddit_raw.get("posts", reddit_raw.get("results", []))
demo["/reddit"] = (reddit_raw or [])[:20]
trends_raw = d.get("apify_results", {}).get("google_trends", [])
if isinstance(trends_raw, dict):
    trends_raw = trends_raw.get("terms", trends_raw.get("results", []))
demo["/trends"] = (trends_raw or [])[:20]

# /config, /summary, /
demo["/config"] = {"mode": "analyst", "temperature": 0.3}
demo["/summary"] = {"status": "demo", "sources": list(d.keys()), "generated_at": d["generated_at"]}
demo["/"] = {"status": "ok", "mode": "demo", "version": "1.0.0"}

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
