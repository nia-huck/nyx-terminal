"""Nyx Terminal — Configuracion del agente y del sistema.

Guarda config en config.json (local) y expone via API.
El frontend lee/escribe esta config para el panel de settings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_FILE = Path(__file__).parent.parent / "config.json"

# ── Defaults ──────────────────────────────────────────

DEFAULTS = {
    # ── API Keys ──
    "anthropic_api_key": "",         # Se puede override desde .env o UI
    "apify_token": "",               # Se puede override desde .env o UI

    # ── Modelo Claude ──
    "model": "claude-sonnet-4-6",    # claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-6
    "max_tokens": 4096,              # Tokens maximos de respuesta
    "temperature": 0.3,              # 0=determinista, 1=creativo

    # ── Modo de operacion ──
    "mode": "analyst",               # analyst | researcher | monitor
    # analyst: responde preguntas con datos locales, economico y conciso
    # researcher: busca mas profundo, usa Apify, cruza fuentes, mas largo
    # monitor: modo alerta, detecta cambios y genera insights automaticos

    # ── Budget Apify ──
    "max_budget_per_query": 0.50,    # USD max por consulta
    "max_live_calls": 2,             # Busquedas live max por consulta
    "apify_enabled": True,           # Habilitar/deshabilitar Apify

    # ── Comportamiento ──
    "language": "es-AR",             # Idioma de respuesta
    "max_iterations": 8,             # Iteraciones max del loop agente
    "save_context": True,            # Guardar insights en PostgreSQL
    "use_db_context": True,          # Buscar contexto previo en DB
    "db_context_limit": 10,          # Max resultados de contexto DB

    # ── PostgreSQL ──
    "database_url": "",              # Override desde .env o UI
    "db_enabled": True,              # Habilitar/deshabilitar PostgreSQL

    # ── System prompt override ──
    "system_prompt_extra": "",       # Instrucciones adicionales al agente
    "persona": "Nyx",               # Nombre del agente
}

# Opciones validas para campos enum
VALID_OPTIONS = {
    "model": [
        {"value": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5 (rapido, barato)", "speed": "fast", "cost": "$"},
        {"value": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (equilibrado)", "speed": "medium", "cost": "$$"},
        {"value": "claude-opus-4-6", "label": "Claude Opus 4.6 (maximo poder)", "speed": "slow", "cost": "$$$"},
    ],
    "mode": [
        {"value": "analyst", "label": "Analista", "description": "Respuestas concisas con datos. Usa data local primero. Ideal para consultas rapidas."},
        {"value": "researcher", "label": "Investigador", "description": "Busca profundo, cruza fuentes, usa Apify. Respuestas mas largas y detalladas."},
        {"value": "monitor", "label": "Monitor", "description": "Detecta cambios, genera alertas e insights automaticos. Escribe contexto al DB."},
    ],
    "language": [
        {"value": "es-AR", "label": "Español argentino"},
        {"value": "es", "label": "Español neutro"},
        {"value": "en", "label": "English"},
    ],
}

# Metadata de campos para el UI
FIELD_META = {
    "anthropic_api_key": {"type": "secret", "label": "Anthropic API Key", "group": "api_keys", "placeholder": "sk-ant-..."},
    "apify_token": {"type": "secret", "label": "Apify Token", "group": "api_keys", "placeholder": "apify_api_..."},
    "model": {"type": "select", "label": "Modelo Claude", "group": "model"},
    "max_tokens": {"type": "number", "label": "Max tokens respuesta", "group": "model", "min": 256, "max": 8192, "step": 256},
    "temperature": {"type": "range", "label": "Temperatura", "group": "model", "min": 0, "max": 1, "step": 0.1},
    "mode": {"type": "select", "label": "Modo de operacion", "group": "behavior"},
    "max_budget_per_query": {"type": "number", "label": "Budget Apify por consulta (USD)", "group": "budget", "min": 0, "max": 5, "step": 0.1},
    "max_live_calls": {"type": "number", "label": "Busquedas live max", "group": "budget", "min": 0, "max": 10, "step": 1},
    "apify_enabled": {"type": "toggle", "label": "Habilitar Apify", "group": "budget"},
    "language": {"type": "select", "label": "Idioma", "group": "behavior"},
    "max_iterations": {"type": "number", "label": "Iteraciones max agente", "group": "behavior", "min": 1, "max": 15, "step": 1},
    "save_context": {"type": "toggle", "label": "Guardar insights en DB", "group": "database"},
    "use_db_context": {"type": "toggle", "label": "Usar contexto previo", "group": "database"},
    "db_context_limit": {"type": "number", "label": "Resultados contexto DB", "group": "database", "min": 1, "max": 50, "step": 1},
    "database_url": {"type": "text", "label": "Database URL", "group": "database", "placeholder": "postgresql://nyx:nyx@localhost:5432/nyx"},
    "db_enabled": {"type": "toggle", "label": "Habilitar PostgreSQL", "group": "database"},
    "system_prompt_extra": {"type": "textarea", "label": "Instrucciones extra", "group": "advanced", "placeholder": "Instrucciones adicionales para el agente..."},
    "persona": {"type": "text", "label": "Nombre del agente", "group": "advanced"},
}

GROUPS = {
    "api_keys": {"label": "API Keys", "icon": "key", "order": 1},
    "model": {"label": "Modelo IA", "icon": "cpu", "order": 2},
    "behavior": {"label": "Comportamiento", "icon": "sliders", "order": 3},
    "budget": {"label": "Budget & Apify", "icon": "dollar", "order": 4},
    "database": {"label": "Base de Datos", "icon": "database", "order": 5},
    "advanced": {"label": "Avanzado", "icon": "settings", "order": 6},
}


# ═══════════════════════════════════════════════════════
#  LOAD / SAVE
# ═══════════════════════════════════════════════════════

def _load_file() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_file(data: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_config() -> dict:
    """Retorna config completa (defaults + overrides de archivo + env)."""
    import os
    file_cfg = _load_file()
    merged = {**DEFAULTS, **file_cfg}

    # Env vars tienen prioridad maxima
    if os.getenv("ANTHROPIC_API_KEY"):
        merged["anthropic_api_key"] = os.getenv("ANTHROPIC_API_KEY")
    if os.getenv("APIFY_TOKEN"):
        merged["apify_token"] = os.getenv("APIFY_TOKEN")
    if os.getenv("DATABASE_URL"):
        merged["database_url"] = os.getenv("DATABASE_URL")

    return merged


def update_config(updates: dict) -> dict:
    """Actualiza campos especificos. No toca env vars."""
    current = _load_file()
    # Solo aceptar campos conocidos
    for key, value in updates.items():
        if key in DEFAULTS:
            current[key] = value
    _save_file(current)
    return get_config()


def get_field(key: str) -> Any:
    return get_config().get(key, DEFAULTS.get(key))


def get_config_schema() -> dict:
    """Retorna el schema completo para que el frontend renderice el formulario."""
    cfg = get_config()
    fields = []
    for key, meta in FIELD_META.items():
        field = {
            "key": key,
            "value": cfg.get(key, DEFAULTS.get(key)),
            "default": DEFAULTS.get(key),
            **meta,
        }
        if key in VALID_OPTIONS:
            field["options"] = VALID_OPTIONS[key]
        # Ocultar valores de secrets (mostrar solo si están configurados)
        if meta["type"] == "secret" and field["value"]:
            field["is_set"] = True
            field["display_value"] = field["value"][:8] + "..." + field["value"][-4:]
        fields.append(field)

    return {
        "fields": fields,
        "groups": GROUPS,
        "config": {k: v for k, v in cfg.items() if FIELD_META.get(k, {}).get("type") != "secret"},
    }
