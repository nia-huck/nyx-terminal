"""Nyx Terminal — Context Writer.

El agente IA usa este modulo para escribir contexto nuevo a PostgreSQL.
Cada vez que el agente aprende algo nuevo (scraping, analisis, insight),
lo persiste aqui para que futuras consultas tengan mas contexto.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from core import db


# ═══════════════════════════════════════════════════════
#  ESCRIBIR INSIGHTS DEL AGENTE
# ═══════════════════════════════════════════════════════

def guardar_insight(titulo: str, contenido: str, *,
                    tags: list[str] | None = None,
                    fuentes: list[str] | None = None,
                    relevancia: float = 7.0,
                    vigencia_dias: int = 7) -> int:
    """El agente guarda un insight/conclusion que aprendio."""
    return db.escribir_contexto(
        tipo="insight",
        titulo=titulo,
        contenido=contenido,
        relevancia=relevancia,
        tags=tags,
        fuentes=fuentes,
        vigente_hasta=date.today() + timedelta(days=vigencia_dias),
    )


def guardar_alerta(titulo: str, contenido: str, *,
                   tags: list[str] | None = None,
                   urgencia: float = 8.0,
                   vigencia_dias: int = 3) -> int:
    """El agente registra una alerta de mercado."""
    return db.escribir_contexto(
        tipo="alerta",
        titulo=titulo,
        contenido=contenido,
        relevancia=urgencia,
        tags=tags,
        vigente_hasta=date.today() + timedelta(days=vigencia_dias),
    )


def guardar_tendencia(titulo: str, contenido: str, *,
                      tags: list[str] | None = None,
                      vigencia_dias: int = 14) -> int:
    """El agente registra una tendencia detectada."""
    return db.escribir_contexto(
        tipo="tendencia",
        titulo=titulo,
        contenido=contenido,
        relevancia=6.0,
        tags=tags,
        vigente_hasta=date.today() + timedelta(days=vigencia_dias),
    )


def guardar_resumen_diario(contenido: str, *, fecha: date | None = None) -> int:
    """El agente guarda un resumen diario del estado economico."""
    f = fecha or date.today()
    return db.escribir_contexto(
        tipo="resumen_diario",
        titulo=f"Resumen economico {f.isoformat()}",
        contenido=contenido,
        relevancia=5.0,
        tags=["resumen", "diario"],
        vigente_hasta=f + timedelta(days=30),
    )


# ═══════════════════════════════════════════════════════
#  INGERIR DATA NUEVA (desde scraping Apify)
# ═══════════════════════════════════════════════════════

def ingerir_noticias(items: list[dict], fuente: str = "apify") -> int:
    """Ingiere noticias nuevas desde scraping."""
    count = 0
    for item in items:
        nid = db.insert_noticia(
            titulo=item.get("title", item.get("titulo", ""))[:500],
            resumen=item.get("description", item.get("resumen", ""))[:2000],
            texto=item.get("text", item.get("markdown", ""))[:10000],
            url=item.get("url", item.get("link")),
            fuente=fuente,
            categoria=item.get("categoria"),
            fecha=_try_parse_dt(item.get("date", item.get("fecha"))),
        )
        if nid:
            count += 1
    return count


def ingerir_tweets(tweets: list[dict], query: str | None = None, fuente: str = "apify") -> int:
    """Ingiere tweets nuevos desde scraping."""
    count = 0
    for tw in tweets:
        tid = db.insert_tweet(
            tweet_id=str(tw.get("id", "")),
            texto=tw.get("full_text", tw.get("text", ""))[:1000],
            autor=(tw.get("author", {}).get("screen_name", "")
                   if isinstance(tw.get("author"), dict)
                   else str(tw.get("author", ""))),
            likes=tw.get("favorite_count", tw.get("likeCount", tw.get("likes", 0))) or 0,
            retweets=tw.get("retweet_count", tw.get("retweetCount", tw.get("retweets", 0))) or 0,
            query_origen=query,
            fecha=_try_parse_dt(tw.get("created_at")),
            url=tw.get("url"),
            fuente=fuente,
        )
        if tid:
            count += 1
    return count


def ingerir_cotizaciones(tipo: str, data: list[dict], fuente: str = "apify") -> int:
    """Ingiere cotizaciones nuevas (dolar, riesgo pais, etc)."""
    rows = []
    for d in data:
        f = _try_parse_date(d.get("fecha", d.get("date")))
        if not f:
            continue
        rows.append({
            "tipo": tipo,
            "fecha": f,
            "compra": d.get("compra"),
            "venta": d.get("venta"),
            "valor": d.get("valor", d.get("value")),
            "fuente": fuente,
        })
    db.upsert_cotizaciones_batch(rows)
    return len(rows)


# ═══════════════════════════════════════════════════════
#  GUARDAR SNAPSHOT DEL MOTOR MATEMATICO
# ═══════════════════════════════════════════════════════

def guardar_snapshot_nyx(datos_indice: dict):
    """Guarda un snapshot del indice Nyx para tracking historico."""
    db.guardar_snapshot("indice_nyx", datos_indice)


def guardar_snapshot_reporte(datos_reporte: dict):
    """Guarda un snapshot del reporte completo."""
    db.guardar_snapshot("reporte_completo", datos_reporte)


# ═══════════════════════════════════════════════════════
#  CONSULTAR CONTEXTO (para el agente)
# ═══════════════════════════════════════════════════════

def obtener_contexto_relevante(query: str, limite: int = 10) -> list[dict]:
    """El agente busca contexto previo relevante a una consulta."""
    return db.buscar_contexto(query, limite)


def obtener_alertas_activas(limite: int = 10) -> list[dict]:
    """Obtiene alertas vigentes ordenadas por urgencia."""
    return db.get_contexto_reciente(tipo="alerta", limite=limite)


def buscar_en_todo(query: str, limite: int = 20) -> list[dict]:
    """Busqueda full-text en toda la base de datos."""
    return db.buscar_todo(query, limite)


# ═══════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════

def _try_parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s)
    except Exception:
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(s)
        except Exception:
            return None


def _try_parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00").split("T")[0]).date()
    except Exception:
        return None
