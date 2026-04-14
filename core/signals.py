"""Nyx Terminal — Senales derivadas del cruce de datos."""

from __future__ import annotations
from core.store import DataStore


def brecha_cambiaria(store: DataStore) -> dict | None:
    """Calcula brecha entre dolar blue y oficial."""
    tipos = store.dolar_actual()
    blue = oficial = None
    for d in tipos:
        nombre = d.get("nombre", d.get("casa", "")).lower()
        if "blue" in nombre:
            blue = d.get("venta")
        elif "oficial" in nombre:
            oficial = d.get("venta")
    if blue and oficial and oficial > 0:
        brecha = ((blue - oficial) / oficial) * 100
        return {
            "blue_venta": blue,
            "oficial_venta": oficial,
            "brecha_pct": round(brecha, 2),
            "alerta": brecha > 30 or brecha < -5,
        }
    return None


def tasa_real(store: DataStore) -> dict | None:
    """BADLAR vs inflacion interanual estimada."""
    badlar = store.tasa_badlar()
    inflacion = store.inflacion_mensual(12)
    if not badlar or not inflacion:
        return None
    tasa_nominal = badlar.get("v", badlar.get("valor", 0))
    if isinstance(tasa_nominal, str):
        try:
            tasa_nominal = float(tasa_nominal)
        except ValueError:
            return None
    # Inflacion interanual aproximada (suma de ultimos 12 meses)
    inf_anual = 0
    for m in inflacion:
        val = m.get("valor", m.get("value", 0))
        if isinstance(val, (int, float)):
            inf_anual += val
    tasa_r = tasa_nominal - inf_anual
    return {
        "badlar": round(tasa_nominal, 2),
        "inflacion_12m": round(inf_anual, 2),
        "tasa_real": round(tasa_r, 2),
        "negativa": tasa_r < 0,
    }


def tendencia_reservas(store: DataStore) -> dict | None:
    """Tendencia de reservas internacionales (30 dias)."""
    var = store.bcra_variable("reservas_internacionales")
    if not var:
        return None
    data = var.get("last_30d", [])
    if len(data) < 2:
        return None
    # Ordenar por fecha ascendente (BCRA data viene descendente)
    pares = []
    for d in data:
        v = d.get("v", d.get("valor", 0))
        f = d.get("fecha", "")
        if isinstance(v, (int, float)):
            pares.append((f, v))
    pares.sort(key=lambda x: x[0])
    if len(pares) < 2:
        return None
    inicio = pares[0][1]
    actual = pares[-1][1]
    cambio = actual - inicio
    cambio_pct = (cambio / inicio * 100) if inicio else 0
    return {
        "actual_usd_mm": round(actual, 0),
        "inicio_periodo": round(inicio, 0),
        "cambio_usd_mm": round(cambio, 0),
        "cambio_pct": round(cambio_pct, 2),
        "tendencia": "sube" if cambio > 0 else "baja" if cambio < 0 else "estable",
        "dias": len(pares),
    }


def presion_cambiaria(store: DataStore) -> dict:
    """Indicador compuesto de presion cambiaria (0-100)."""
    score = 50  # base neutral
    components = {}

    # Brecha cambiaria
    brecha = brecha_cambiaria(store)
    if brecha:
        b = brecha["brecha_pct"]
        components["brecha"] = b
        if b > 50:
            score += 20
        elif b > 30:
            score += 10
        elif b < 5:
            score -= 10

    # Riesgo pais
    rp = store.riesgo_pais()
    if rp:
        val = rp.get("v", rp.get("valor", 0))
        if isinstance(val, (int, float)):
            components["riesgo_pais"] = val
            if val > 1500:
                score += 15
            elif val > 1000:
                score += 5
            elif val < 700:
                score -= 10

    # Tasa real negativa
    tr = tasa_real(store)
    if tr:
        components["tasa_real"] = tr["tasa_real"]
        if tr["negativa"]:
            score += 10

    # Reservas cayendo
    res = tendencia_reservas(store)
    if res:
        components["reservas_tendencia"] = res["tendencia"]
        if res["tendencia"] == "baja":
            score += 10
        elif res["tendencia"] == "sube":
            score -= 5

    score = max(0, min(100, score))
    return {
        "score": score,
        "nivel": "critico" if score > 75 else "alto" if score > 60 else "moderado" if score > 40 else "bajo",
        "components": components,
    }


def all_signals(store: DataStore) -> dict:
    """Calcula todas las senales disponibles."""
    return {
        "brecha_cambiaria": brecha_cambiaria(store),
        "tasa_real": tasa_real(store),
        "tendencia_reservas": tendencia_reservas(store),
        "presion_cambiaria": presion_cambiaria(store),
    }
