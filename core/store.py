"""Nyx Terminal — DataStore: carga y acceso a toda la data de info/."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent / "info"


def _load(rel_path: str) -> dict | list | None:
    fp = BASE / rel_path
    if fp.exists():
        with open(fp, encoding="utf-8") as f:
            return json.load(f)
    return None


class DataStore:
    """Centraliza el acceso a toda la data descargada en info/."""

    def __init__(self):
        self.loaded_at: str = datetime.now().isoformat()
        self._cache: dict[str, any] = {}

    # ── Quick loaders ──────────────────────────────

    @property
    def quick(self) -> dict:
        if "quick" not in self._cache:
            self._cache["quick"] = _load("_quick_load.json") or {}
        return self._cache["quick"]

    @property
    def index(self) -> dict:
        if "index" not in self._cache:
            self._cache["index"] = _load("_index.json") or {}
        return self._cache["index"]

    @property
    def news_digest(self) -> dict:
        if "digest" not in self._cache:
            self._cache["digest"] = _load("_news_digest.json") or {}
        return self._cache["digest"]

    # ── Dolar ──────────────────────────────────────

    def dolar_actual(self) -> list[dict]:
        return self.quick.get("dolar_actual", [])

    def dolar_blue(self) -> dict | None:
        for d in self.dolar_actual():
            if d.get("casa") == "blue" or d.get("nombre") == "Blue":
                return d
        return None

    def dolar_historial(self, tipo: str = "blue", dias: int = 30) -> list[dict]:
        key = f"dolar_{tipo}_30d"
        data = self.quick.get(key, [])
        return data[-dias:]

    # ── BCRA ───────────────────────────────────────

    def bcra_variable(self, nombre: str) -> dict | None:
        bcra = self.quick.get("bcra", {})
        return bcra.get(nombre)

    def bcra_current(self, nombre: str) -> dict | None:
        var = self.bcra_variable(nombre)
        if var:
            return var.get("current")
        return None

    def reservas(self) -> dict | None:
        return self.bcra_current("reservas_internacionales")

    def tasa_badlar(self) -> dict | None:
        return self.bcra_current("tasa_badlar")

    def base_monetaria(self) -> dict | None:
        return self.bcra_current("base_monetaria")

    # ── Riesgo pais ────────────────────────────────

    def riesgo_pais(self) -> dict | None:
        rp = self.quick.get("riesgo_pais", {})
        return rp.get("current")

    def riesgo_pais_historial(self, dias: int = 30) -> list[dict]:
        rp = self.quick.get("riesgo_pais", {})
        return rp.get("last_30d", [])[-dias:]

    # ── Inflacion ──────────────────────────────────

    def inflacion_mensual(self, meses: int = 12) -> list:
        return self.quick.get("inflacion_mensual", [])[-meses:]

    # ── Series temporales ──────────────────────────

    def serie(self, nombre: str) -> dict | None:
        return self.quick.get(nombre)

    # ── Tasas y rendimientos ──────────────────────

    def tasas_plazo_fijo(self) -> list[dict]:
        return self.quick.get("tasas_plazo_fijo", [])

    def rendimientos_crypto(self) -> list[dict]:
        return self.quick.get("rendimientos", [])

    def bluelytics(self) -> dict:
        return self.quick.get("bluelytics", {})

    # ── Noticias ───────────────────────────────────

    def noticias(self, fuente: str | None = None) -> list[dict]:
        sources = self.news_digest.get("sources", {})
        if fuente:
            return sources.get(fuente, [])
        all_items = []
        for items in sources.values():
            if isinstance(items, list):
                all_items.extend(items)
        return all_items

    # ── Tweets ─────────────────────────────────────

    def tweets(self, query: str | None = None) -> list[dict]:
        if query:
            data = _load(f"twitter/{query}.json")
            return data if isinstance(data, list) else []
        meta = _load("twitter/_all_twitter.json")
        if not meta:
            return []
        all_tw = []
        for qname, items in meta.get("queries", {}).items():
            if isinstance(items, list):
                all_tw.extend(items)
        return all_tw

    # ── Reddit ─────────────────────────────────────

    def reddit(self, sub: str | None = None) -> list[dict]:
        if sub:
            data = _load(f"reddit/{sub}.json")
            return data if isinstance(data, list) else []
        meta = _load("reddit/_all_reddit.json")
        if not meta:
            return []
        all_posts = []
        for sname, items in meta.get("subreddits", {}).items():
            if isinstance(items, list):
                all_posts.extend(items)
        return all_posts

    # ── Trends ─────────────────────────────────────

    def trends(self) -> list[dict]:
        data = _load("trends/google_trends_ar.json")
        if data:
            return data.get("trends", [])
        return []

    # ── Resumen del store ──────────────────────────

    def summary(self) -> dict:
        idx = self.index
        return {
            "loaded_at": self.loaded_at,
            "total_files": idx.get("total_files", 0),
            "total_size_mb": idx.get("total_size_mb", 0),
            "categories": list(idx.get("structure", {}).keys()),
            "dolar_blue": self.dolar_blue(),
            "riesgo_pais": self.riesgo_pais(),
            "total_noticias": self.news_digest.get("total_items", 0),
        }
