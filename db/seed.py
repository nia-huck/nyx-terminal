"""Nyx Terminal — Seed PostgreSQL desde info/ JSONs.

Migra todos los datos cacheados a la base de datos.
Ejecutar una vez, luego el agente actualiza incrementalmente.

Uso:
    python -m db.seed
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, date
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import db

BASE = Path(__file__).parent.parent / "info"


def _load(rel: str) -> dict | list | None:
    fp = BASE / rel
    if fp.exists():
        with open(fp, encoding="utf-8") as f:
            return json.load(f)
    return None


def _parse_fecha(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00").split("T")[0]).date()
    except Exception:
        return None


def _parse_datetime(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s)
    except Exception:
        try:
            # RFC 2822 style: "Mon, 14 Apr 2026 ..."
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(s)
        except Exception:
            return None


def seed_cotizaciones():
    """Dolar (7 tipos x 90 dias), riesgo pais, inflacion, IPC, EMAE."""
    print("  Cotizaciones...")
    count = 0

    # Dolar historial (90 dias x 7 tipos)
    for tipo in ["blue", "oficial", "bolsa", "contadoconliqui", "mayorista", "cripto", "tarjeta"]:
        data = _load(f"apis/dolar_historial_{tipo}.json")
        if not data:
            continue
        rows = []
        for d in data:
            f = _parse_fecha(d.get("fecha"))
            if not f:
                continue
            rows.append({
                "tipo": f"dolar_{tipo}",
                "fecha": f,
                "compra": d.get("compra"),
                "venta": d.get("venta"),
                "fuente": "seed",
            })
        db.upsert_cotizaciones_batch(rows)
        count += len(rows)

    # Riesgo pais (90 dias)
    rp = _load("apis/riesgo_pais_historial.json")
    if rp:
        rows = []
        for d in rp:
            f = _parse_fecha(d.get("fecha"))
            if not f:
                continue
            rows.append({"tipo": "riesgo_pais", "fecha": f, "valor": d.get("valor"), "fuente": "seed"})
        db.upsert_cotizaciones_batch(rows)
        count += len(rows)

    # Inflacion mensual (60 meses)
    inf = _load("apis/ar_inflacion_mensual.json")
    if inf:
        rows = []
        for d in inf:
            f = _parse_fecha(d.get("fecha"))
            if not f:
                continue
            rows.append({"tipo": "inflacion_mensual", "fecha": f, "valor": d.get("valor"), "fuente": "seed"})
        db.upsert_cotizaciones_batch(rows)
        count += len(rows)

    # IPC Nacional + Nucleo (24 meses)
    ql = _load("_quick_load.json")
    if ql:
        for serie_name in ["ipc_nacional", "ipc_nucleo", "emae", "tipo_cambio_nominal"]:
            serie = ql.get(serie_name, {})
            data = serie.get("data", [])
            rows = []
            for d in data:
                if len(d) >= 2 and d[1] is not None:
                    f = _parse_fecha(d[0])
                    if f:
                        rows.append({"tipo": serie_name, "fecha": f, "valor": d[1], "fuente": "seed"})
            db.upsert_cotizaciones_batch(rows)
            count += len(rows)

    print(f"    {count} cotizaciones insertadas")


def seed_bcra():
    """Variables BCRA (16 variables x 60 dias)."""
    print("  BCRA variables...")
    data = _load("apis/bcra_monetarias_historial.json")
    if not data:
        print("    Sin datos BCRA historial")
        return

    count = 0
    for var_name, var_data in data.get("variables", {}).items():
        rows = []
        for d in var_data.get("data", []):
            f = _parse_fecha(d.get("fecha"))
            v = d.get("valor")
            if f and v is not None:
                rows.append({"variable": var_name, "fecha": f, "valor": v, "fuente": "seed"})
        db.upsert_bcra_batch(rows)
        count += len(rows)

    print(f"    {count} registros BCRA insertados")


def seed_noticias():
    """RSS feeds + articulos + RAG."""
    print("  Noticias...")
    count = 0

    # RSS digest
    digest = _load("_news_digest.json")
    if digest:
        for fuente, items in digest.get("sources", {}).items():
            if not isinstance(items, list):
                continue
            for item in items:
                nid = db.insert_noticia(
                    titulo=item.get("titulo", item.get("title", ""))[:500],
                    resumen=item.get("resumen", item.get("description", ""))[:2000],
                    url=item.get("link", item.get("url")),
                    fuente=fuente,
                    categoria="economia",
                    fecha=_parse_datetime(item.get("fecha", item.get("date"))),
                )
                if nid:
                    count += 1

    # Articles (full text)
    for fname in ["infobae_economia", "lanacion_economia", "ambito_finanzas", "iprofesional_finanzas"]:
        articles = _load(f"articles/{fname}.json")
        if not articles or not isinstance(articles, list):
            continue
        for item in articles:
            nid = db.insert_noticia(
                titulo=item.get("title", "")[:500],
                resumen=item.get("description", "")[:2000],
                texto=item.get("text", "")[:10000],
                url=item.get("url"),
                fuente=f"article_{fname}",
                categoria="economia",
                fecha=_parse_datetime(item.get("date")),
                autor=", ".join(item.get("author", [])) if isinstance(item.get("author"), list) else item.get("author"),
            )
            if nid:
                count += 1

    # RAG documents — extract title from first line of markdown if empty
    import re
    for fp in (BASE / "rag").glob("*.json"):
        if fp.name.startswith("_"):
            continue
        data = _load(f"rag/{fp.name}")
        if not data or not isinstance(data, list):
            continue
        tema = fp.stem
        for item in data:
            markdown = item.get("markdown", "") or ""
            url = item.get("url", "") or ""
            title = item.get("title", "") or ""

            if not title and markdown:
                first_line = markdown.split("\n")[0].strip()
                first_line = re.sub(r"^#+\s*", "", first_line)
                first_line = re.sub(r"<[^>]+>", "", first_line)
                title = first_line[:200] if first_line else tema.replace("_", " ").title()
            if not title:
                title = tema.replace("_", " ").title()
            if not markdown:
                continue

            nid = db.insert_noticia(
                titulo=title[:500],
                texto=markdown[:10000],
                url=url if url else None,
                fuente=f"rag_{tema}",
                categoria=tema,
            )
            if nid:
                count += 1

    print(f"    {count} noticias insertadas")


def seed_tweets():
    """7,414 tweets de 12 busquedas."""
    print("  Tweets...")
    count = 0

    for fp in (BASE / "twitter").glob("*.json"):
        if fp.name.startswith("_"):
            continue
        query_name = fp.stem
        data = _load(f"twitter/{fp.name}")
        if not data or not isinstance(data, list):
            continue

        for tw in data:
            tid = db.insert_tweet(
                tweet_id=str(tw.get("id", "")),
                texto=tw.get("text", "")[:1000],
                autor=tw.get("author", ""),
                likes=tw.get("likes", 0) or 0,
                retweets=tw.get("retweets", 0) or 0,
                replies=tw.get("replies", 0) or 0,
                query_origen=query_name,
                fecha=_parse_datetime(tw.get("created_at")),
                url=tw.get("url"),
                fuente="seed",
            )
            if tid:
                count += 1

    print(f"    {count} tweets insertados")


def seed_reddit():
    """Reddit posts."""
    print("  Reddit...")
    count = 0

    for fp in (BASE / "reddit").glob("*.json"):
        if fp.name.startswith("_"):
            continue
        sub_name = fp.stem
        data = _load(f"reddit/{fp.name}")
        if not data or not isinstance(data, list):
            continue

        for post in data:
            rid = db.insert_reddit(
                post_id=str(post.get("url", f"{sub_name}_{count}")),
                titulo=post.get("title", "")[:500],
                cuerpo=post.get("body", "")[:5000],
                autor=post.get("author", ""),
                score=post.get("score", 0) or 0,
                comentarios=post.get("comments", 0) or 0,
                subreddit=sub_name,
                url=post.get("url"),
                fecha=_parse_datetime(post.get("created")),
                fuente="seed",
            )
            if rid:
                count += 1

    print(f"    {count} reddit posts insertados")


def seed_rendimientos():
    """Plazo fijo + crypto yields."""
    print("  Rendimientos...")
    count = 0
    ql = _load("_quick_load.json")
    if not ql:
        return

    # Plazo fijo
    for e in ql.get("tasas_plazo_fijo", []):
        tna = e.get("tnaClientes") or e.get("tnaNoClientes")
        if tna:
            with db.get_pool().connection() as conn:
                conn.execute("""
                    INSERT INTO rendimientos (tipo, entidad, moneda, tasa, fecha, fuente)
                    VALUES ('plazo_fijo', %s, 'ARS', %s, %s, 'seed')
                    ON CONFLICT (tipo, entidad, moneda, fecha) DO NOTHING
                """, [e.get("entidad", "?"), tna * 100, date.today()])
                count += 1

    # Crypto
    for plat in ql.get("rendimientos", []):
        entidad = plat.get("entidad", "?")
        for r in plat.get("rendimientos", []):
            apy = r.get("apy")
            if apy and apy > 0:
                f = _parse_fecha(r.get("fecha")) or date.today()
                with db.get_pool().connection() as conn:
                    conn.execute("""
                        INSERT INTO rendimientos (tipo, entidad, moneda, tasa, fecha, fuente)
                        VALUES ('crypto', %s, %s, %s, %s, 'seed')
                        ON CONFLICT (tipo, entidad, moneda, fecha) DO NOTHING
                    """, [entidad, r.get("moneda", "?"), apy, f])
                    count += 1

    print(f"    {count} rendimientos insertados")


def seed_trends():
    """Google Trends."""
    print("  Trends...")
    data = _load("trends/google_trends_ar.json")
    if not data:
        return

    count = 0
    for trend in data.get("trends", []):
        term = trend.get("term", "")
        for point in trend.get("timeline", []):
            vals = point.get("value", [])
            if vals and vals[0] is not None:
                f_str = point.get("formattedTime", "")
                # Parse "Mar 13, 2026" style
                try:
                    f = datetime.strptime(f_str, "%b %d, %Y").date()
                except Exception:
                    continue
                with db.get_pool().connection() as conn:
                    conn.execute("""
                        INSERT INTO trends (termino, fecha, valor, fuente)
                        VALUES (%s, %s, %s, 'seed')
                        ON CONFLICT (termino, fecha) DO NOTHING
                    """, [term, f, vals[0]])
                    count += 1

    print(f"    {count} trends insertados")


def run_seed():
    """Ejecuta todo el seed."""
    print("=" * 50)
    print("NYX TERMINAL — Seed PostgreSQL")
    print("=" * 50)

    seed_cotizaciones()
    seed_bcra()
    seed_noticias()
    seed_tweets()
    seed_reddit()
    seed_rendimientos()
    seed_trends()

    print()
    print("=== STATS FINALES ===")
    stats = db.stats()
    for table, count in stats.items():
        print(f"  {table}: {count}")
    print()
    print("Seed completado.")


if __name__ == "__main__":
    run_seed()
