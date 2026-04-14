"""Nyx Terminal — Modulo PostgreSQL.

Connection pool + operaciones CRUD para todas las tablas.
El agente y el scraper usan este modulo para leer/escribir contexto.
"""

from __future__ import annotations

import os
from datetime import datetime, date
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    """Obtiene o crea el pool de conexiones."""
    global _pool
    if _pool is None:
        dsn = os.getenv("DATABASE_URL", "postgresql://nyx:nyx@localhost:5432/nyx")
        _pool = ConnectionPool(dsn, min_size=2, max_size=10, kwargs={"row_factory": dict_row})
    return _pool


def close_pool():
    global _pool
    if _pool:
        _pool.close()
        _pool = None


# ═══════════════════════════════════════════════════════
#  COTIZACIONES
# ═══════════════════════════════════════════════════════

def upsert_cotizacion(tipo: str, fecha: date, *, compra: float | None = None,
                      venta: float | None = None, valor: float | None = None,
                      fuente: str = "seed", meta: dict | None = None):
    with get_pool().connection() as conn:
        conn.execute("""
            INSERT INTO cotizaciones (tipo, fecha, compra, venta, valor, fuente, meta)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tipo, fecha) DO UPDATE SET
                compra = COALESCE(EXCLUDED.compra, cotizaciones.compra),
                venta = COALESCE(EXCLUDED.venta, cotizaciones.venta),
                valor = COALESCE(EXCLUDED.valor, cotizaciones.valor),
                fuente = EXCLUDED.fuente,
                meta = COALESCE(EXCLUDED.meta, cotizaciones.meta)
        """, [tipo, fecha, compra, venta, valor, fuente, psycopg.types.json.Json(meta) if meta else None])


def upsert_cotizaciones_batch(rows: list[dict]):
    """Batch upsert. Cada row: {tipo, fecha, compra?, venta?, valor?, fuente?, meta?}"""
    if not rows:
        return
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute("""
                    INSERT INTO cotizaciones (tipo, fecha, compra, venta, valor, fuente, meta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tipo, fecha) DO UPDATE SET
                        compra = COALESCE(EXCLUDED.compra, cotizaciones.compra),
                        venta = COALESCE(EXCLUDED.venta, cotizaciones.venta),
                        valor = COALESCE(EXCLUDED.valor, cotizaciones.valor),
                        fuente = EXCLUDED.fuente
                """, [r["tipo"], r["fecha"], r.get("compra"), r.get("venta"),
                      r.get("valor"), r.get("fuente", "seed"), None])


def get_cotizacion(tipo: str, dias: int = 30) -> list[dict]:
    with get_pool().connection() as conn:
        return conn.execute(
            "SELECT * FROM cotizaciones WHERE tipo = %s ORDER BY fecha DESC LIMIT %s",
            [tipo, dias]
        ).fetchall()


def get_cotizacion_actual(tipo: str) -> dict | None:
    with get_pool().connection() as conn:
        return conn.execute(
            "SELECT * FROM cotizaciones WHERE tipo = %s ORDER BY fecha DESC LIMIT 1",
            [tipo]
        ).fetchone()


# ═══════════════════════════════════════════════════════
#  BCRA VARIABLES
# ═══════════════════════════════════════════════════════

def upsert_bcra(variable: str, fecha: date, valor: float, fuente: str = "seed"):
    with get_pool().connection() as conn:
        conn.execute("""
            INSERT INTO bcra_variables (variable, fecha, valor, fuente)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (variable, fecha) DO UPDATE SET valor = EXCLUDED.valor, fuente = EXCLUDED.fuente
        """, [variable, fecha, valor, fuente])


def upsert_bcra_batch(rows: list[dict]):
    if not rows:
        return
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute("""
                    INSERT INTO bcra_variables (variable, fecha, valor, fuente)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (variable, fecha) DO UPDATE SET valor = EXCLUDED.valor
                """, [r["variable"], r["fecha"], r["valor"], r.get("fuente", "seed")])


def get_bcra(variable: str, dias: int = 30) -> list[dict]:
    with get_pool().connection() as conn:
        return conn.execute(
            "SELECT * FROM bcra_variables WHERE variable = %s ORDER BY fecha DESC LIMIT %s",
            [variable, dias]
        ).fetchall()


# ═══════════════════════════════════════════════════════
#  NOTICIAS
# ═══════════════════════════════════════════════════════

def insert_noticia(*, titulo: str, resumen: str | None = None, texto: str | None = None,
                   url: str | None = None, fuente: str = "", categoria: str | None = None,
                   fecha: datetime | None = None, autor: str | None = None,
                   meta: dict | None = None) -> int | None:
    # Normalizar URL vacia a None
    if url is not None and not url.strip():
        url = None
    with get_pool().connection() as conn:
        if url:
            row = conn.execute("""
                INSERT INTO noticias (titulo, resumen, texto, url, fuente, categoria, fecha, autor, meta)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) WHERE url IS NOT NULL AND url != '' DO NOTHING
                RETURNING id
            """, [titulo, resumen, texto, url, fuente, categoria, fecha, autor,
                  psycopg.types.json.Json(meta) if meta else None]).fetchone()
        else:
            row = conn.execute("""
                INSERT INTO noticias (titulo, resumen, texto, url, fuente, categoria, fecha, autor, meta)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, [titulo, resumen, texto, None, fuente, categoria, fecha, autor,
                  psycopg.types.json.Json(meta) if meta else None]).fetchone()
        return row["id"] if row else None


def buscar_noticias(query: str, limite: int = 20) -> list[dict]:
    with get_pool().connection() as conn:
        return conn.execute("""
            SELECT id, titulo, resumen, fuente, categoria, fecha,
                   ts_rank(tsv, websearch_to_tsquery('spanish', %s)) as rank
            FROM noticias
            WHERE tsv @@ websearch_to_tsquery('spanish', %s)
            ORDER BY rank DESC, fecha DESC
            LIMIT %s
        """, [query, query, limite]).fetchall()


def get_noticias_recientes(limite: int = 50, fuente: str | None = None) -> list[dict]:
    with get_pool().connection() as conn:
        if fuente:
            return conn.execute(
                "SELECT id, titulo, resumen, fuente, fecha FROM noticias WHERE fuente = %s ORDER BY fecha DESC LIMIT %s",
                [fuente, limite]
            ).fetchall()
        return conn.execute(
            "SELECT id, titulo, resumen, fuente, fecha FROM noticias ORDER BY fecha DESC LIMIT %s",
            [limite]
        ).fetchall()


# ═══════════════════════════════════════════════════════
#  TWEETS
# ═══════════════════════════════════════════════════════

def insert_tweet(*, tweet_id: str | None = None, texto: str, autor: str | None = None,
                 likes: int = 0, retweets: int = 0, replies: int = 0,
                 query_origen: str | None = None, fecha: datetime | None = None,
                 url: str | None = None, fuente: str = "seed") -> int | None:
    with get_pool().connection() as conn:
        row = conn.execute("""
            INSERT INTO tweets (tweet_id, texto, autor, likes, retweets, replies, query_origen, fecha, url, fuente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tweet_id) DO NOTHING
            RETURNING id
        """, [tweet_id, texto, autor, likes, retweets, replies, query_origen, fecha, url, fuente]).fetchone()
        return row["id"] if row else None


def buscar_tweets(query: str, limite: int = 20) -> list[dict]:
    with get_pool().connection() as conn:
        return conn.execute("""
            SELECT id, texto, autor, likes, retweets, query_origen, fecha,
                   ts_rank(tsv, websearch_to_tsquery('spanish', %s)) as rank
            FROM tweets
            WHERE tsv @@ websearch_to_tsquery('spanish', %s)
            ORDER BY rank DESC, fecha DESC
            LIMIT %s
        """, [query, query, limite]).fetchall()


# ═══════════════════════════════════════════════════════
#  REDDIT
# ═══════════════════════════════════════════════════════

def insert_reddit(*, post_id: str | None = None, titulo: str, cuerpo: str | None = None,
                  autor: str | None = None, score: int = 0, comentarios: int = 0,
                  subreddit: str | None = None, url: str | None = None,
                  fecha: datetime | None = None, fuente: str = "seed") -> int | None:
    with get_pool().connection() as conn:
        row = conn.execute("""
            INSERT INTO reddit_posts (post_id, titulo, cuerpo, autor, score, comentarios, subreddit, url, fecha, fuente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (post_id) DO NOTHING
            RETURNING id
        """, [post_id, titulo, cuerpo, autor, score, comentarios, subreddit, url, fecha, fuente]).fetchone()
        return row["id"] if row else None


# ═══════════════════════════════════════════════════════
#  EVENTOS
# ═══════════════════════════════════════════════════════

def insert_evento(*, titulo: str, tipo: str, urgencia: int = 5, sector: list | None = None,
                  activos: list | None = None, provincia: str | None = None,
                  lat: float | None = None, lon: float | None = None,
                  fecha: datetime | None = None, resumen: str | None = None,
                  fuente: str | None = None, fuente_url: str | None = None,
                  horizonte: str | None = None, noticia_id: int | None = None,
                  fuente_tipo: str = "classifier", meta: dict | None = None) -> int:
    with get_pool().connection() as conn:
        row = conn.execute("""
            INSERT INTO eventos (titulo, tipo, urgencia, sector, activos_afectados, provincia,
                                 lat, lon, fecha, resumen, fuente, fuente_url, horizonte,
                                 noticia_id, fuente_tipo, meta)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, [titulo, tipo, urgencia, sector, activos, provincia, lat, lon, fecha, resumen,
              fuente, fuente_url, horizonte, noticia_id, fuente_tipo,
              psycopg.types.json.Json(meta) if meta else None]).fetchone()
        return row["id"]


# ═══════════════════════════════════════════════════════
#  CONTEXTO AGENTE — El agente escribe insights aqui
# ═══════════════════════════════════════════════════════

def escribir_contexto(*, tipo: str, titulo: str, contenido: str,
                      relevancia: float = 5.0, tags: list | None = None,
                      fuentes: list | None = None, vigente_hasta: date | None = None,
                      meta: dict | None = None) -> int:
    with get_pool().connection() as conn:
        row = conn.execute("""
            INSERT INTO agente_contexto (tipo, titulo, contenido, relevancia, tags, fuentes, vigente_hasta, meta)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, [tipo, titulo, contenido, relevancia, tags, fuentes, vigente_hasta,
              psycopg.types.json.Json(meta) if meta else None]).fetchone()
        return row["id"]


def buscar_contexto(query: str, limite: int = 10) -> list[dict]:
    """Busca en la tabla de contexto del agente."""
    with get_pool().connection() as conn:
        return conn.execute("""
            SELECT id, tipo, titulo, contenido, relevancia, tags, created_at,
                   ts_rank(tsv, websearch_to_tsquery('spanish', %s)) as rank
            FROM agente_contexto
            WHERE tsv @@ websearch_to_tsquery('spanish', %s)
              AND (vigente_hasta IS NULL OR vigente_hasta >= CURRENT_DATE)
            ORDER BY rank DESC, relevancia DESC
            LIMIT %s
        """, [query, query, limite]).fetchall()


def get_contexto_reciente(tipo: str | None = None, limite: int = 20) -> list[dict]:
    with get_pool().connection() as conn:
        if tipo:
            return conn.execute(
                """SELECT * FROM agente_contexto
                   WHERE tipo = %s AND (vigente_hasta IS NULL OR vigente_hasta >= CURRENT_DATE)
                   ORDER BY created_at DESC LIMIT %s""",
                [tipo, limite]
            ).fetchall()
        return conn.execute(
            """SELECT * FROM agente_contexto
               WHERE vigente_hasta IS NULL OR vigente_hasta >= CURRENT_DATE
               ORDER BY created_at DESC LIMIT %s""",
            [limite]
        ).fetchall()


# ═══════════════════════════════════════════════════════
#  SNAPSHOTS
# ═══════════════════════════════════════════════════════

def guardar_snapshot(tipo: str, datos: dict):
    with get_pool().connection() as conn:
        conn.execute(
            "INSERT INTO snapshots (tipo, datos) VALUES (%s, %s)",
            [tipo, psycopg.types.json.Json(datos)]
        )


def get_ultimo_snapshot(tipo: str) -> dict | None:
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT * FROM snapshots WHERE tipo = %s ORDER BY fecha DESC LIMIT 1",
            [tipo]
        ).fetchone()
        return row


# ═══════════════════════════════════════════════════════
#  BUSQUEDA UNIFICADA — Full-text across all tables
# ═══════════════════════════════════════════════════════

def buscar_todo(query: str, limite: int = 20) -> list[dict]:
    """Busqueda full-text en todas las tablas con texto indexado."""
    with get_pool().connection() as conn:
        return conn.execute(
            "SELECT * FROM buscar_contexto(%s, %s)",
            [query, limite]
        ).fetchall()


# ═══════════════════════════════════════════════════════
#  ESTADISTICAS
# ═══════════════════════════════════════════════════════

def stats() -> dict:
    """Retorna conteos de todas las tablas."""
    with get_pool().connection() as conn:
        counts = {}
        for table in ["cotizaciones", "bcra_variables", "noticias", "tweets",
                       "reddit_posts", "eventos", "agente_contexto", "snapshots",
                       "trends", "rendimientos"]:
            row = conn.execute(f"SELECT COUNT(*) as n FROM {table}").fetchone()
            counts[table] = row["n"]
        return counts
