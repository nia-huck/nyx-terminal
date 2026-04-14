"""Nyx Terminal — Organizar toda la data en estructura final para hackathon"""
import json
import os
from datetime import datetime

BASE = "info"

def load(path):
    full = os.path.join(BASE, path)
    if os.path.exists(full):
        with open(full, encoding="utf-8") as f:
            return json.load(f)
    return None

def save(path, data):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    size = os.path.getsize(full)
    print(f"  >> {full} ({size//1024}KB)")
    return size

def p(msg): print(msg)

p("="*60)
p("ORGANIZANDO DATA PARA HACKATHON")
p("="*60)

# ═══════════════════════════════════════
# MASTER INDEX — mapa de toda la data
# ═══════════════════════════════════════
index = {
    "generated_at": datetime.now().isoformat(),
    "hackathon_date": "2026-04-14",
    "structure": {},
}

total_size = 0
file_count = 0
for root, dirs, files in os.walk(BASE):
    for fname in files:
        if fname.endswith(".json") and fname != "_index.json":
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, BASE).replace("\\", "/")
            size = os.path.getsize(full_path)
            total_size += size
            file_count += 1

            # Categorize
            category = rel_path.split("/")[0]
            if category not in index["structure"]:
                index["structure"][category] = []

            # Get record count
            try:
                data = json.load(open(full_path, encoding="utf-8"))
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict):
                    # Try to count main data
                    for key in ["tipos", "variables", "data", "feeds", "queries", "trends", "posts", "subreddits", "sites"]:
                        if key in data:
                            v = data[key]
                            count = len(v) if isinstance(v, (list, dict)) else 0
                            break
                    else:
                        count = len(data)
                else:
                    count = 0
            except:
                count = 0

            index["structure"][category].append({
                "file": rel_path,
                "size_kb": size // 1024,
                "records": count,
            })

index["total_files"] = file_count
index["total_size_kb"] = total_size // 1024
index["total_size_mb"] = round(total_size / (1024*1024), 2)

save("_index.json", index)

# ═══════════════════════════════════════
# QUICK-LOAD — datos mas importantes en 1 archivo
# ═══════════════════════════════════════
p("\n=== Building quick-load.json (datos clave en 1 archivo) ===")

quick = {"generated_at": datetime.now().isoformat()}

# Dolar actual
dolar = load("apis/dolar_todos.json")
if dolar:
    quick["dolar_actual"] = dolar.get("tipos", dolar)

# Dolar historial (solo blue y oficial, ultimos 30)
for tipo in ["blue", "oficial", "bolsa", "contadoconliqui", "mayorista"]:
    hist = load(f"apis/dolar_historial_{tipo}.json")
    if hist and isinstance(hist, list):
        quick[f"dolar_{tipo}_30d"] = hist[-30:]

# BCRA variables principales
bcra = load("apis/bcra_monetarias_historial.json")
if bcra and "variables" in bcra:
    quick["bcra"] = {}
    for vname, vdata in bcra["variables"].items():
        if isinstance(vdata, dict) and "data" in vdata:
            quick["bcra"][vname] = {
                "current": vdata["data"][0] if vdata["data"] else None,
                "last_30d": vdata["data"][:30],
            }

# Riesgo pais
rp = load("apis/riesgo_pais_historial.json")
if rp and isinstance(rp, list):
    quick["riesgo_pais"] = {"current": rp[-1], "last_30d": rp[-30:]}

# IPC y EMAE
series = load("apis/series_temporales.json")
if series and "series" in series:
    for sname, sdata in series["series"].items():
        if isinstance(sdata, dict) and "data" in sdata:
            quick[sname] = sdata

# Inflacion
inf = load("apis/ar_inflacion_mensual.json")
if inf and isinstance(inf, list):
    quick["inflacion_mensual"] = inf[-24:]

# Tasas
tasas = load("apis/ar_tasas_plazo_fijo.json")
if tasas:
    quick["tasas_plazo_fijo"] = tasas

# Rendimientos
rend = load("apis/ar_rendimientos.json")
if rend:
    quick["rendimientos"] = rend

# Bluelytics
bly = load("apis/bluelytics_latest.json")
if bly:
    quick["bluelytics"] = bly

save("_quick_load.json", quick)

# ═══════════════════════════════════════
# NEWS DIGEST — todas las noticias en 1 archivo
# ═══════════════════════════════════════
p("\n=== Building news-digest.json ===")
digest = {"generated_at": datetime.now().isoformat(), "sources": {}, "total_items": 0}

# RSS
for fname in ["ambito_economia", "cronista", "economista_finanzas", "economista_economia", "economista_internacional"]:
    data = load(f"news/{fname}.json")
    if data and isinstance(data, list):
        digest["sources"][f"rss_{fname}"] = data
        digest["total_items"] += len(data)

# Articles (if available)
for fname in ["infobae_economia", "pagina12_economia", "lanacion_economia", "ambito_finanzas", "iprofesional_finanzas"]:
    data = load(f"articles/{fname}.json")
    if data and isinstance(data, list):
        digest["sources"][f"article_{fname}"] = data
        digest["total_items"] += len(data)

# RAG results (if available)
for fname in os.listdir(os.path.join(BASE, "rag")) if os.path.exists(os.path.join(BASE, "rag")) else []:
    if fname.startswith("_"):
        continue
    data = load(f"rag/{fname}")
    if data and isinstance(data, list):
        qname = fname.replace(".json", "")
        digest["sources"][f"rag_{qname}"] = data
        digest["total_items"] += len(data)

save("_news_digest.json", digest)
p(f"  Total items en digest: {digest['total_items']}")

# ═══════════════════════════════════════
# REPORT
# ═══════════════════════════════════════
p(f"""
{'='*60}
NYX TERMINAL — DATA ORGANIZADA
{'='*60}

Carpeta: info/
Archivos: {file_count}
Tamano total: {total_size//1024} KB ({round(total_size/(1024*1024),2)} MB)

Estructura:""")

for cat, files in index["structure"].items():
    cat_size = sum(f["size_kb"] for f in files)
    p(f"  {cat}/ ({len(files)} archivos, {cat_size}KB)")
    for f in files:
        p(f"    {f['file']} ({f['size_kb']}KB, {f['records']} records)")

p(f"""
Archivos clave para el hackathon:
  info/_quick_load.json   — Datos economicos esenciales (1 archivo)
  info/_news_digest.json  — Todas las noticias consolidadas
  info/_index.json        — Indice de toda la data
""")
