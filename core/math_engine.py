"""Nyx Terminal — Motor de analisis matematico.

Calcula metricas derivadas, series temporales, indicadores macro
y rankings a partir de la data cruda en info/.
Todas las funciones son puras (no hacen llamadas externas).
"""

from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from core.store import DataStore

BASE = Path(__file__).parent.parent / "info"


def _load(rel_path: str) -> dict | list | None:
    fp = BASE / rel_path
    if fp.exists():
        with open(fp, encoding="utf-8") as f:
            return json.load(f)
    return None


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", ""))
        except ValueError:
            return None
    return None


def _pct_change(old: float, new: float) -> float | None:
    if old and old != 0:
        return round(((new - old) / abs(old)) * 100, 2)
    return None


def _dias_entre(fecha_a: str, fecha_b: str) -> int:
    """Dias calendario entre dos fechas ISO."""
    try:
        a = datetime.fromisoformat(fecha_a.split("T")[0])
        b = datetime.fromisoformat(fecha_b.split("T")[0])
        return abs((b - a).days)
    except Exception:
        return 0


def _sort_by_fecha(data: list[dict], key: str = "fecha") -> list[dict]:
    """Ordena lista de dicts por fecha ascendente."""
    def parse(d):
        f = d.get(key, "")
        try:
            return datetime.fromisoformat(f.replace("Z", "+00:00") if "T" in f else f)
        except Exception:
            return datetime.min
    return sorted(data, key=parse)


# ═══════════════════════════════════════════════════════
#  DOLAR — Velocidad, volatilidad, spreads
# ═══════════════════════════════════════════════════════

def dolar_velocidad(store: DataStore) -> dict:
    """Velocidad de cambio del dolar (todos los tipos disponibles)."""
    tipos = ["blue", "oficial", "bolsa", "contadoconliqui", "mayorista", "cripto", "tarjeta"]
    resultado = {}

    for tipo in tipos:
        hist = _load(f"apis/dolar_historial_{tipo}.json")
        if not hist or len(hist) < 2:
            continue

        hist = _sort_by_fecha(hist)
        ventas = [_safe_float(d.get("venta")) for d in hist]
        ventas = [v for v in ventas if v is not None]

        if len(ventas) < 2:
            continue

        actual = ventas[-1]
        hace_7d = ventas[-7] if len(ventas) >= 7 else ventas[0]
        hace_30d = ventas[-30] if len(ventas) >= 30 else ventas[0]
        inicio = ventas[0]

        # Daily returns for volatility
        returns = []
        for i in range(1, len(ventas)):
            if ventas[i - 1] > 0:
                returns.append((ventas[i] - ventas[i - 1]) / ventas[i - 1])

        vol = round(statistics.stdev(returns) * 100, 3) if len(returns) >= 2 else None

        resultado[tipo] = {
            "actual": actual,
            "var_7d_pct": _pct_change(hace_7d, actual),
            "var_30d_pct": _pct_change(hace_30d, actual),
            "var_90d_pct": _pct_change(inicio, actual),
            "min_90d": round(min(ventas), 2),
            "max_90d": round(max(ventas), 2),
            "volatilidad_diaria_pct": vol,
            "tendencia": "sube" if actual > hace_30d else "baja" if actual < hace_30d else "estable",
            "datos": len(ventas),
        }

    return resultado


def dolar_spreads(store: DataStore) -> dict:
    """Spreads entre tipos de dolar — MEP vs Blue, CCL vs Blue, etc."""
    tipos_map = {}
    for d in store.dolar_actual():
        casa = d.get("casa", "").lower()
        venta = _safe_float(d.get("venta"))
        if venta:
            tipos_map[casa] = venta

    spreads = {}
    blue = tipos_map.get("blue")
    oficial = tipos_map.get("oficial")
    mep = tipos_map.get("bolsa")  # "bolsa" = MEP
    ccl = tipos_map.get("contadoconliqui")
    mayorista = tipos_map.get("mayorista")

    if blue and oficial:
        spreads["blue_vs_oficial"] = {
            "diferencia": round(blue - oficial, 2),
            "brecha_pct": _pct_change(oficial, blue),
        }
    if mep and blue:
        spreads["mep_vs_blue"] = {
            "diferencia": round(mep - blue, 2),
            "brecha_pct": _pct_change(blue, mep),
        }
    if ccl and blue:
        spreads["ccl_vs_blue"] = {
            "diferencia": round(ccl - blue, 2),
            "brecha_pct": _pct_change(blue, ccl),
        }
    if ccl and mep:
        spreads["ccl_vs_mep"] = {
            "diferencia": round(ccl - mep, 2),
            "brecha_pct": _pct_change(mep, ccl),
        }
    if oficial and mayorista:
        spreads["oficial_vs_mayorista"] = {
            "diferencia": round(oficial - mayorista, 2),
            "brecha_pct": _pct_change(mayorista, oficial),
        }

    # Convergencia: si todos los spreads se achican → convergencia
    if mep and blue and ccl:
        rango = max(mep, blue, ccl) - min(mep, blue, ccl)
        promedio = (mep + blue + ccl) / 3
        dispersion_pct = round((rango / promedio) * 100, 2) if promedio > 0 else 0
        spreads["convergencia"] = {
            "rango_pesos": round(rango, 2),
            "dispersion_pct": dispersion_pct,
            "nivel": "alta" if dispersion_pct < 2 else "moderada" if dispersion_pct < 5 else "baja",
        }

    return spreads


def dolar_blend(store: DataStore) -> dict:
    """Dolar blend: promedio ponderado de tipos libres (Blue, MEP, CCL)."""
    tipos_map = {}
    for d in store.dolar_actual():
        casa = d.get("casa", "").lower()
        venta = _safe_float(d.get("venta"))
        if venta:
            tipos_map[casa] = venta

    blue = tipos_map.get("blue", 0)
    mep = tipos_map.get("bolsa", 0)
    ccl = tipos_map.get("contadoconliqui", 0)

    valores = [v for v in [blue, mep, ccl] if v > 0]
    if not valores:
        return {}

    blend = round(sum(valores) / len(valores), 2)
    return {
        "blend": blend,
        "componentes": {"blue": blue, "mep": mep, "ccl": ccl},
        "fecha": datetime.now().strftime("%Y-%m-%d"),
    }


# ═══════════════════════════════════════════════════════
#  BCRA — Monetarias, reservas, dolar implicito
# ═══════════════════════════════════════════════════════

def dolar_implicito(store: DataStore) -> dict | None:
    """Dolar implicito = Base Monetaria / Reservas Internacionales.
    Estimacion teorica del tipo de cambio de equilibrio monetario."""
    bm = store.bcra_variable("base_monetaria")
    res = store.bcra_variable("reservas_internacionales")

    if not bm or not res:
        return None

    bm_val = _safe_float(bm.get("current", {}).get("valor"))
    res_val = _safe_float(res.get("current", {}).get("valor"))

    if not bm_val or not res_val or res_val == 0:
        return None

    # Base monetaria en millones de pesos, reservas en millones de USD
    implicito = round(bm_val / res_val, 2)

    # Con circulacion monetaria (mas conservador)
    circ = store.bcra_variable("circulacion_monetaria")
    implicito_circ = None
    if circ:
        circ_val = _safe_float(circ.get("current", {}).get("valor"))
        if circ_val:
            implicito_circ = round(circ_val / res_val, 2)

    # Comparar con blue actual
    blue = store.dolar_blue()
    blue_venta = _safe_float(blue.get("venta")) if blue else None

    return {
        "dolar_implicito_base": implicito,
        "dolar_implicito_circulacion": implicito_circ,
        "base_monetaria_mm": round(bm_val, 0),
        "reservas_usd_mm": round(res_val, 0),
        "blue_actual": blue_venta,
        "ratio_blue_vs_implicito": round(blue_venta / implicito, 2) if blue_venta and implicito > 0 else None,
        "interpretacion": (
            "blue por encima del implicito — expectativas de devaluacion"
            if blue_venta and implicito and blue_venta > implicito * 1.1
            else "blue alineado al implicito — equilibrio monetario"
            if blue_venta and implicito and abs(blue_venta - implicito) / implicito < 0.1
            else "blue por debajo del implicito — exceso de confianza o intervencion"
            if blue_venta and implicito
            else None
        ),
    }


def reservas_velocidad(store: DataStore) -> dict | None:
    """Velocidad de cambio de reservas internacionales (USD/dia calendario)."""
    data = _load("apis/bcra_monetarias_historial.json")
    if not data:
        return None

    res_data = data.get("variables", {}).get("reservas_internacionales", {}).get("data", [])
    if len(res_data) < 2:
        return None

    res_data = _sort_by_fecha(res_data)
    valores = [(d.get("fecha"), _safe_float(d.get("valor"))) for d in res_data]
    valores = [(f, v) for f, v in valores if f and v is not None]

    if len(valores) < 2:
        return None

    actual_fecha, actual = valores[-1]
    inicio_fecha, inicio = valores[0]

    # Usar dias CALENDARIO reales, no cantidad de data points
    dias_cal = _dias_entre(inicio_fecha, actual_fecha)
    if dias_cal <= 0:
        dias_cal = len(valores)

    cambio_total = actual - inicio
    usd_por_dia = round(cambio_total / dias_cal, 1)

    # Ultimo tramo: buscar el punto mas cercano a 7 dias atras
    if len(valores) >= 3:
        ref_fecha, ref_val = valores[-7] if len(valores) >= 7 else valores[0]
        dias_7d = _dias_entre(ref_fecha, actual_fecha)
        if dias_7d <= 0:
            dias_7d = 7
        cambio_7d = actual - ref_val
        usd_dia_7d = round(cambio_7d / dias_7d, 1)
    else:
        usd_dia_7d = usd_por_dia

    return {
        "actual_usd_mm": round(actual, 0),
        "cambio_total_usd_mm": round(cambio_total, 0),
        "usd_por_dia": usd_por_dia,
        "usd_por_dia_7d": usd_dia_7d,
        "dias_calendario": dias_cal,
        "datos": len(valores),
        "acelerando": usd_dia_7d > usd_por_dia if usd_por_dia > 0 else usd_dia_7d < usd_por_dia,
        "tendencia": "acumulando" if usd_por_dia > 0 else "perdiendo" if usd_por_dia < 0 else "estable",
    }


def expansion_monetaria(store: DataStore) -> dict | None:
    """Expansion de base monetaria vs inflacion — senial de presion futura."""
    data = _load("apis/bcra_monetarias_historial.json")
    if not data:
        return None

    bm_data = data.get("variables", {}).get("base_monetaria", {}).get("data", [])
    if len(bm_data) < 2:
        return None

    bm_data = _sort_by_fecha(bm_data)
    pares = [(d.get("fecha", ""), _safe_float(d.get("valor"))) for d in bm_data]
    pares = [(f, v) for f, v in pares if f and v is not None]

    if len(pares) < 2:
        return None

    bm_actual = pares[-1][1]
    bm_inicio = pares[0][1]
    bm_var_pct = _pct_change(bm_inicio, bm_actual)

    # Calcular meses calendario reales del periodo BM
    dias_periodo = _dias_entre(pares[0][0], pares[-1][0])
    meses_periodo = max(1, round(dias_periodo / 30))

    # Inflacion acumulada en la misma cantidad de meses
    inf = store.inflacion_mensual(meses_periodo)
    inf_acum = 0
    for m in inf:
        v = _safe_float(m.get("valor", m.get("value")))
        if v is not None:
            inf_acum += v

    exceso = round((bm_var_pct or 0) - inf_acum, 2) if bm_var_pct is not None else None

    return {
        "base_monetaria_var_pct": bm_var_pct,
        "inflacion_acum_pct": round(inf_acum, 2),
        "periodo_meses": meses_periodo,
        "exceso_monetario_pct": exceso,
        "presion_inflacionaria": exceso is not None and exceso > 5,
        "interpretacion": (
            "base monetaria crece mas rapido que precios — presion inflacionaria latente"
            if exceso and exceso > 5
            else "expansion monetaria alineada a inflacion"
            if exceso is not None
            else None
        ),
    }


def depositos_ratio(store: DataStore) -> dict | None:
    """Ratio depositos privados vs publicos — proxy de crowding out."""
    priv = store.bcra_variable("depositos_sector_privado")
    pub = store.bcra_variable("depositos_sector_publico")

    if not priv or not pub:
        return None

    priv_val = _safe_float(priv.get("current", {}).get("valor"))
    pub_val = _safe_float(pub.get("current", {}).get("valor"))

    if not priv_val or not pub_val or pub_val == 0:
        return None

    ratio = round(priv_val / pub_val, 4)

    return {
        "depositos_privados_mm": round(priv_val, 0),
        "depositos_publicos_mm": round(pub_val, 0),
        "ratio_priv_pub": ratio,
        "domina": "sector_publico" if ratio < 1 else "sector_privado",
    }


# ═══════════════════════════════════════════════════════
#  INFLACION — Interanual, tendencia, aceleracion
# ═══════════════════════════════════════════════════════

def inflacion_analisis(store: DataStore) -> dict:
    """Analisis completo de inflacion: interanual, tendencia, aceleracion."""
    mensual = store.inflacion_mensual(24)
    if not mensual:
        return {}

    valores = []
    for m in mensual:
        v = _safe_float(m.get("valor", m.get("value")))
        f = m.get("fecha", "")
        if v is not None:
            valores.append({"fecha": f, "valor": v})

    if len(valores) < 2:
        return {}

    vals = [v["valor"] for v in valores]

    # Interanual: producto de (1 + mes/100) para ultimos 12 meses
    ultimos_12 = vals[-12:] if len(vals) >= 12 else vals
    interanual_prod = 1.0
    for v in ultimos_12:
        interanual_prod *= (1 + v / 100)
    interanual = round((interanual_prod - 1) * 100, 2)

    # Interanual simple (suma)
    interanual_simple = round(sum(ultimos_12), 2)

    # Acumulado ultimo trimestre
    ultimos_3 = vals[-3:] if len(vals) >= 3 else vals
    acum_3m = round(sum(ultimos_3), 2)

    # Tendencia: promedio movil 3 meses
    if len(vals) >= 6:
        avg_reciente = statistics.mean(vals[-3:])
        avg_anterior = statistics.mean(vals[-6:-3])
        aceleracion = round(avg_reciente - avg_anterior, 2)
        tendencia = "acelerando" if aceleracion > 0.3 else "desacelerando" if aceleracion < -0.3 else "estable"
    else:
        aceleracion = None
        tendencia = "sin_datos"

    # Anualizada desde ultimo mes
    ultimo_mes = vals[-1]
    anualizada_ultimo = round(((1 + ultimo_mes / 100) ** 12 - 1) * 100, 2)

    return {
        "ultimo_mes": vals[-1],
        "fecha_ultimo": valores[-1]["fecha"],
        "interanual_compuesta": interanual,
        "interanual_simple": interanual_simple,
        "acumulada_3m": acum_3m,
        "anualizada_ultimo_mes": anualizada_ultimo,
        "promedio_3m": round(statistics.mean(ultimos_3), 2),
        "promedio_6m": round(statistics.mean(vals[-6:]), 2) if len(vals) >= 6 else None,
        "aceleracion": aceleracion,
        "tendencia": tendencia,
        "meses_analizados": len(vals),
        "serie": valores[-12:],
    }


# ═══════════════════════════════════════════════════════
#  ACTIVIDAD — EMAE (Estimador Mensual de Actividad)
# ═══════════════════════════════════════════════════════

def actividad_emae(store: DataStore) -> dict:
    """Analisis de actividad economica via EMAE."""
    emae = store.serie("emae")
    if not emae or not emae.get("data"):
        return {}

    data = emae["data"]
    # Format: [["2025-01-01", 149.04], ...]
    puntos = [(d[0], d[1]) for d in data if len(d) == 2 and d[1] is not None]
    if len(puntos) < 2:
        return {}

    vals = [p[1] for p in puntos]
    actual = vals[-1]
    anterior = vals[-2]
    hace_12 = vals[-12] if len(vals) >= 12 else vals[0]

    mom = _pct_change(anterior, actual)
    yoy = _pct_change(hace_12, actual)

    # Tendencia 3 meses
    if len(vals) >= 4:
        avg_3 = statistics.mean(vals[-3:])
        avg_prev = statistics.mean(vals[-6:-3]) if len(vals) >= 6 else vals[-4]
        if isinstance(avg_prev, (int, float)):
            tendencia_pct = _pct_change(avg_prev, avg_3)
        else:
            tendencia_pct = None
    else:
        tendencia_pct = None

    return {
        "actual": round(actual, 2),
        "fecha": puntos[-1][0],
        "var_mensual_pct": mom,
        "var_interanual_pct": yoy,
        "tendencia_3m_pct": tendencia_pct,
        "max_24m": round(max(vals), 2),
        "min_24m": round(min(vals), 2),
        "estado": (
            "expansion" if yoy and yoy > 2
            else "estancamiento" if yoy and abs(yoy) <= 2
            else "contraccion" if yoy and yoy < -2
            else "sin_datos"
        ),
    }


# ═══════════════════════════════════════════════════════
#  TASAS — Tasa real, carry trade, ranking plazo fijo
# ═══════════════════════════════════════════════════════

def tasas_reales(store: DataStore) -> dict:
    """Tasa real para cada tipo de tasa disponible."""
    inf_data = inflacion_analisis(store)
    inf_anual = inf_data.get("interanual_compuesta", 0)
    inf_mensual = inf_data.get("ultimo_mes", 0)

    tasas_nombres = {
        "tasa_badlar": "BADLAR",
        "tasa_tm20": "TM20",
        "tasa_depositos_30d": "Depositos 30d",
        "tasa_baibar": "BAIBAR",
        "tasa_pases_pasivos": "Pases pasivos (ref BCRA)",
    }

    resultado = {}
    for key, label in tasas_nombres.items():
        var = store.bcra_variable(key)
        if not var or not var.get("current"):
            continue
        tna = _safe_float(var["current"].get("valor"))
        if tna is None:
            continue

        # TEA = (1 + TNA/365*30)^(365/30) - 1
        tea = ((1 + tna / 100 / 365 * 30) ** (365 / 30) - 1) * 100
        tasa_real = round(tea - inf_anual, 2)

        # Tasa real mensual
        tasa_mensual = round(tna / 12, 2)
        real_mensual = round(tasa_mensual - inf_mensual, 2)

        resultado[key] = {
            "nombre": label,
            "tna": round(tna, 2),
            "tea": round(tea, 2),
            "inflacion_anual": round(inf_anual, 2),
            "tasa_real_anual": tasa_real,
            "tasa_mensual": tasa_mensual,
            "real_mensual": real_mensual,
            "positiva": tasa_real > 0,
        }

    return resultado


def carry_trade(store: DataStore) -> dict:
    """Retorno del carry trade: plazo fijo en pesos vs devaluacion del blue."""
    # Devaluacion mensual del blue
    vel = dolar_velocidad(store)
    blue_vel = vel.get("blue", {})
    devaluacion_30d = blue_vel.get("var_30d_pct", 0) or 0

    # Mejor tasa plazo fijo
    pf = store.quick.get("tasas_plazo_fijo", [])
    if not pf:
        return {}

    tasas = []
    for e in pf:
        tna = _safe_float(e.get("tnaClientes"))
        if tna and tna > 0:
            mensual = tna / 12 * 100  # TNA es fraccion (0.26 = 26%)
            tasas.append({
                "entidad": e.get("entidad", "?"),
                "tna_pct": round(tna * 100, 2),
                "rendimiento_mensual_pct": round(mensual, 2),
            })

    tasas.sort(key=lambda x: x["rendimiento_mensual_pct"], reverse=True)
    mejor = tasas[0] if tasas else {}

    ganancia_carry = round(mejor.get("rendimiento_mensual_pct", 0) - devaluacion_30d, 2) if mejor else None

    return {
        "mejor_plazo_fijo": mejor,
        "top_5": tasas[:5],
        "devaluacion_blue_30d_pct": round(devaluacion_30d, 2),
        "ganancia_carry_mensual_pct": ganancia_carry,
        "carry_positivo": ganancia_carry is not None and ganancia_carry > 0,
        "interpretacion": (
            f"carry trade positivo: plazo fijo rinde {ganancia_carry}% mas que devaluacion"
            if ganancia_carry and ganancia_carry > 0
            else "carry trade negativo: el dolar sube mas rapido que el plazo fijo"
            if ganancia_carry
            else None
        ),
    }


def ranking_plazo_fijo(store: DataStore) -> list[dict]:
    """Ranking de plazo fijo por TNA, con calculo de rendimiento real."""
    pf = store.quick.get("tasas_plazo_fijo", [])
    inf = inflacion_analisis(store)
    inf_mensual = inf.get("ultimo_mes", 0)

    ranking = []
    for e in pf:
        tna_c = _safe_float(e.get("tnaClientes"))
        tna_nc = _safe_float(e.get("tnaNoClientes"))
        tna = tna_c or tna_nc
        if not tna or tna <= 0:
            continue

        tna_pct = tna * 100
        mensual = tna_pct / 12
        real_mensual = mensual - inf_mensual

        ranking.append({
            "entidad": e.get("entidad", "?"),
            "tna_pct": round(tna_pct, 2),
            "rendimiento_mensual_pct": round(mensual, 2),
            "real_vs_inflacion": round(real_mensual, 2),
            "le_gana_inflacion": real_mensual > 0,
        })

    ranking.sort(key=lambda x: x["tna_pct"], reverse=True)
    return ranking


# ═══════════════════════════════════════════════════════
#  CRYPTO — Ranking rendimientos stablecoins y crypto
# ═══════════════════════════════════════════════════════

def ranking_crypto_yields(store: DataStore) -> dict:
    """Ranking de rendimientos crypto por moneda y plataforma."""
    rendimientos = store.quick.get("rendimientos", [])
    if not rendimientos:
        return {}

    # Agrupar por moneda
    por_moneda: dict[str, list] = {}
    for plat in rendimientos:
        entidad = plat.get("entidad", "?")
        for r in plat.get("rendimientos", []):
            moneda = r.get("moneda", "?")
            apy = _safe_float(r.get("apy"))
            if apy is None or apy <= 0:
                continue
            if moneda not in por_moneda:
                por_moneda[moneda] = []
            por_moneda[moneda].append({
                "plataforma": entidad,
                "apy_pct": round(apy, 2),
            })

    # Ordenar cada moneda por APY descendente
    for moneda in por_moneda:
        por_moneda[moneda].sort(key=lambda x: x["apy_pct"], reverse=True)

    # Stablecoins destacados
    stables = {}
    for coin in ["USDT", "USDC", "DAI"]:
        if coin in por_moneda:
            stables[coin] = {
                "mejor": por_moneda[coin][0] if por_moneda[coin] else None,
                "opciones": len(por_moneda[coin]),
                "rango_apy": [por_moneda[coin][-1]["apy_pct"], por_moneda[coin][0]["apy_pct"]] if por_moneda[coin] else [],
            }

    return {
        "por_moneda": por_moneda,
        "stablecoins": stables,
        "total_opciones": sum(len(v) for v in por_moneda.values()),
    }


# ═══════════════════════════════════════════════════════
#  INFLACION CORE vs HEADLINE
# ═══════════════════════════════════════════════════════

def inflacion_core_vs_headline(store: DataStore) -> dict:
    """Compara IPC nucleo (core) vs IPC nacional (headline).
    Si core > headline: presion inflacionaria subyacente.
    Si core < headline: regulados/estacionales empujan headline."""
    nucleo = store.serie("ipc_nucleo")
    general = store.serie("ipc_nacional")

    if not nucleo or not general:
        return {}

    n_data = nucleo.get("data", [])
    g_data = general.get("data", [])

    if len(n_data) < 2 or len(g_data) < 2:
        return {}

    meses = []
    for i in range(-min(6, len(n_data) - 1, len(g_data) - 1), 0):
        if n_data[i][0] != g_data[i][0]:
            continue
        n_mom = (n_data[i][1] - n_data[i - 1][1]) / n_data[i - 1][1] * 100
        g_mom = (g_data[i][1] - g_data[i - 1][1]) / g_data[i - 1][1] * 100
        meses.append({
            "fecha": n_data[i][0],
            "core_pct": round(n_mom, 2),
            "headline_pct": round(g_mom, 2),
            "spread_pp": round(n_mom - g_mom, 2),
        })

    if not meses:
        return {}

    spread_actual = meses[-1]["spread_pp"]
    spread_promedio = round(sum(m["spread_pp"] for m in meses) / len(meses), 2)

    return {
        "ultimo_mes": meses[-1],
        "spread_actual_pp": spread_actual,
        "spread_promedio_pp": spread_promedio,
        "serie": meses,
        "interpretacion": (
            "inflacion nucleo por encima de general — presion subyacente, regulados frenan headline"
            if spread_actual > 0.2
            else "inflacion nucleo por debajo — ajustes de tarifas/regulados empujan headline"
            if spread_actual < -0.2
            else "core y headline alineados"
        ),
    }


# ═══════════════════════════════════════════════════════
#  INFLACION EXTENDIDA — 60 meses
# ═══════════════════════════════════════════════════════

def inflacion_extendida(store: DataStore) -> dict:
    """Analisis de inflacion con serie completa de 60 meses."""
    data = _load("apis/ar_inflacion_mensual.json")
    if not data:
        return {}

    vals = []
    for m in data:
        v = _safe_float(m.get("valor"))
        f = m.get("fecha", "")
        if v is not None:
            vals.append({"fecha": f, "valor": v})

    if len(vals) < 12:
        return {}

    valores = [v["valor"] for v in vals]

    # Pico historico
    pico = max(valores)
    pico_idx = valores.index(pico)
    pico_fecha = vals[pico_idx]["fecha"]

    # Acumulada desde pico
    desde_pico = valores[pico_idx:]
    acum_desde_pico = 1.0
    for v in desde_pico:
        acum_desde_pico *= (1 + v / 100)
    acum_desde_pico = round((acum_desde_pico - 1) * 100, 2)

    # Acumulada total (60 meses)
    acum_total = 1.0
    for v in valores:
        acum_total *= (1 + v / 100)
    acum_total = round((acum_total - 1) * 100, 2)

    # Promedios por ano
    promedios_anuales = {}
    for v in vals:
        ano = v["fecha"][:4]
        if ano not in promedios_anuales:
            promedios_anuales[ano] = []
        promedios_anuales[ano].append(v["valor"])

    for ano in promedios_anuales:
        meses = promedios_anuales[ano]
        promedios_anuales[ano] = {
            "promedio_mensual": round(sum(meses) / len(meses), 2),
            "meses": len(meses),
        }

    return {
        "meses_totales": len(valores),
        "pico_mensual": pico,
        "pico_fecha": pico_fecha,
        "actual": valores[-1],
        "caida_desde_pico_pp": round(valores[-1] - pico, 2),
        "acumulada_desde_pico_pct": acum_desde_pico,
        "acumulada_total_pct": acum_total,
        "por_ano": promedios_anuales,
    }


# ═══════════════════════════════════════════════════════
#  TASA POLITICA MONETARIA — Pases BCRA
# ═══════════════════════════════════════════════════════

def tasa_politica(store: DataStore) -> dict:
    """Tasa de politica monetaria del BCRA (pases) vs tasas de mercado."""
    pases_p = store.bcra_variable("tasa_pases_pasivos")
    pases_a = store.bcra_variable("tasa_pases_activos")
    badlar = store.bcra_variable("tasa_badlar")

    resultado = {}

    if pases_p and pases_p.get("current"):
        pp_val = _safe_float(pases_p["current"].get("valor"))
        resultado["pases_pasivos"] = pp_val
    if pases_a and pases_a.get("current"):
        pa_val = _safe_float(pases_a["current"].get("valor"))
        resultado["pases_activos"] = pa_val
    if badlar and badlar.get("current"):
        b_val = _safe_float(badlar["current"].get("valor"))
        resultado["badlar"] = b_val

    pp = resultado.get("pases_pasivos")
    bd = resultado.get("badlar")
    if pp and bd:
        resultado["spread_pases_badlar_pp"] = round(pp - bd, 2)
        resultado["interpretacion"] = (
            f"BCRA paga {round(pp - bd, 1)}pp mas que BADLAR por esterilizar — costo fiscal de la politica monetaria"
            if pp > bd
            else "BADLAR por encima de pases — bancos pagan mas que BCRA"
        )

    # Corredor de tasas
    pa = resultado.get("pases_activos")
    if pa and pp:
        resultado["corredor"] = {
            "piso": pa,
            "techo": pp,
            "ancho_pp": round(pp - pa, 2),
        }

    return resultado


# ═══════════════════════════════════════════════════════
#  MULTIPLICADOR MONETARIO
# ═══════════════════════════════════════════════════════

def multiplicador_monetario(store: DataStore) -> dict | None:
    """M2 proxy / Base monetaria = multiplicador del sistema bancario."""
    bm = store.bcra_variable("base_monetaria")
    circ = store.bcra_variable("circulacion_monetaria")
    dep_priv = store.bcra_variable("depositos_sector_privado")

    if not bm or not circ or not dep_priv:
        return None

    bm_val = _safe_float(bm.get("current", {}).get("valor"))
    circ_val = _safe_float(circ.get("current", {}).get("valor"))
    dep_val = _safe_float(dep_priv.get("current", {}).get("valor"))

    if not bm_val or not circ_val or not dep_val or bm_val == 0:
        return None

    m2_proxy = circ_val + dep_val
    multiplicador = round(m2_proxy / bm_val, 3)
    ratio_circ_base = round(circ_val / bm_val * 100, 1)

    return {
        "base_monetaria_mm": round(bm_val, 0),
        "circulacion_mm": round(circ_val, 0),
        "depositos_privados_mm": round(dep_val, 0),
        "m2_proxy_mm": round(m2_proxy, 0),
        "multiplicador": multiplicador,
        "ratio_circulacion_base_pct": ratio_circ_base,
        "interpretacion": (
            "multiplicador alto — sistema bancario apalancado"
            if multiplicador > 2
            else "multiplicador bajo — economia desmonetizada"
            if multiplicador < 0.8
            else "multiplicador normal"
        ),
    }


# ═══════════════════════════════════════════════════════
#  DEPOSITOS TENDENCIA — Fuga o acumulacion
# ═══════════════════════════════════════════════════════

def depositos_tendencia(store: DataStore) -> dict | None:
    """Tendencia de depositos privados y publicos en 30 dias."""
    priv = store.bcra_variable("depositos_sector_privado")
    pub = store.bcra_variable("depositos_sector_publico")

    resultado = {}

    for nombre, var in [("privados", priv), ("publicos", pub)]:
        if not var or not var.get("last_30d"):
            continue
        data = var["last_30d"]
        # Ordenar por fecha ascendente (viene descendente)
        pares = [(d.get("fecha", ""), _safe_float(d.get("valor"))) for d in data]
        pares = [(f, v) for f, v in pares if f and v is not None]
        pares.sort(key=lambda x: x[0])
        if len(pares) < 2:
            continue

        inicio = pares[0][1]
        actual = pares[-1][1]
        cambio_pct = _pct_change(inicio, actual)

        resultado[nombre] = {
            "actual_mm": round(actual, 0),
            "inicio_mm": round(inicio, 0),
            "cambio_pct": cambio_pct,
            "tendencia": "sube" if cambio_pct and cambio_pct > 1 else "baja" if cambio_pct and cambio_pct < -1 else "estable",
        }

    # Dolarizacion proxy: depositos bajan + dolar sube
    if "privados" in resultado:
        dep_trend = resultado["privados"].get("cambio_pct", 0) or 0
        vel = dolar_velocidad(store)
        blue_30d = vel.get("blue", {}).get("var_30d_pct", 0) or 0
        if dep_trend < -2 and blue_30d > 2:
            resultado["alerta_dolarizacion"] = True
            resultado["interpretacion"] = "depositos cayendo mientras dolar sube — posible dolarizacion de carteras"
        elif dep_trend > 2 and blue_30d < -1:
            resultado["interpretacion"] = "depositos creciendo con dolar estable — confianza en pesos"
        else:
            resultado["alerta_dolarizacion"] = False

    return resultado


# ═══════════════════════════════════════════════════════
#  CARRY TRADE MULTI-DOLAR
# ═══════════════════════════════════════════════════════

def carry_trade_multi(store: DataStore) -> dict:
    """Carry trade vs Blue, MEP y CCL."""
    vel = dolar_velocidad(store)

    pf = store.quick.get("tasas_plazo_fijo", [])
    if not pf:
        return {}

    # Mejor tasa
    mejor_tna = 0
    mejor_entidad = "?"
    for e in pf:
        tna = _safe_float(e.get("tnaClientes"))
        if tna and tna > mejor_tna:
            mejor_tna = tna
            mejor_entidad = e.get("entidad", "?")

    if mejor_tna <= 0:
        return {}

    rend_mensual = mejor_tna / 12 * 100

    resultado = {"mejor_plazo_fijo": {"entidad": mejor_entidad, "tna_pct": round(mejor_tna * 100, 2), "mensual_pct": round(rend_mensual, 2)}}

    for tipo_key, tipo_label in [("blue", "Blue"), ("bolsa", "MEP"), ("contadoconliqui", "CCL")]:
        dev = vel.get(tipo_key, {}).get("var_30d_pct", 0) or 0
        ganancia = round(rend_mensual - dev, 2)
        resultado[tipo_label.lower()] = {
            "devaluacion_30d_pct": round(dev, 2),
            "ganancia_carry_pct": ganancia,
            "positivo": ganancia > 0,
        }

    return resultado


# ═══════════════════════════════════════════════════════
#  SENTIMENT SOCIAL — Proxy desde tweets
# ═══════════════════════════════════════════════════════

_POSITIVE_KW = [
    "sube", "subio", "crecimiento", "record", "positivo", "mejora", "baja el dolar",
    "estabilidad", "superavit", "inversion", "optimismo", "recupera", "crece",
    "bajan precios", "desinflacion", "acuerdo", "confianza",
]
_NEGATIVE_KW = [
    "crisis", "cae", "cayo", "devaluacion", "inflacion", "default", "riesgo",
    "cepo", "corralito", "corrida", "panico", "sube el dolar", "ajuste",
    "recesion", "pobreza", "desempleo", "caida", "desplome", "colapso",
    "emergencia", "paro", "huelga", "conflicto",
]


def sentiment_social(store: DataStore) -> dict:
    """Analisis de sentiment basico de tweets por keyword matching."""
    all_tweets = store.tweets()
    if not all_tweets:
        return {}

    total = len(all_tweets)
    positivos = 0
    negativos = 0
    neutros = 0
    engagement_pos = 0
    engagement_neg = 0

    for tw in all_tweets:
        text = tw.get("text", "").lower()
        likes = tw.get("likes", 0) or 0
        rts = tw.get("retweets", 0) or 0
        engagement = likes + rts

        pos = sum(1 for kw in _POSITIVE_KW if kw in text)
        neg = sum(1 for kw in _NEGATIVE_KW if kw in text)

        if pos > neg:
            positivos += 1
            engagement_pos += engagement
        elif neg > pos:
            negativos += 1
            engagement_neg += engagement
        else:
            neutros += 1

    ratio = round(positivos / negativos, 2) if negativos > 0 else None

    # Volumen por query como proxy de tension
    queries_vol = {}
    for qname in ["dolar_blue", "inflacion", "cepo_cambiario", "devaluacion", "riesgo_pais", "paro_sindical"]:
        tw_q = store.tweets(qname)
        if tw_q:
            queries_vol[qname] = len(tw_q)

    return {
        "total_tweets": total,
        "positivos": positivos,
        "negativos": negativos,
        "neutros": neutros,
        "ratio_pos_neg": ratio,
        "engagement_positivo": engagement_pos,
        "engagement_negativo": engagement_neg,
        "tono": (
            "optimista" if ratio and ratio > 1.5
            else "pesimista" if ratio and ratio < 0.7
            else "mixto"
        ),
        "volumen_por_tema": queries_vol,
    }


# ═══════════════════════════════════════════════════════
#  NOTICIAS VOLUMEN — Proxy de crisis
# ═══════════════════════════════════════════════════════

def noticias_volumen(store: DataStore) -> dict:
    """Conteo de noticias por tema como proxy de tension del mercado."""
    noticias = store.noticias()
    if not noticias:
        return {}

    temas = {
        "dolar": 0, "inflacion": 0, "reservas": 0, "cepo": 0,
        "devaluacion": 0, "riesgo_pais": 0, "bcra": 0, "merval": 0,
        "paro": 0, "fmi": 0, "tarifas": 0,
    }

    total = len(noticias)
    for item in noticias:
        texto = (item.get("titulo", "") + " " + item.get("resumen", "") + " " +
                 item.get("title", "") + " " + item.get("text", "")).lower()
        for tema in temas:
            if tema in texto:
                temas[tema] += 1

    # Top temas
    ranking = sorted(temas.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_noticias": total,
        "por_tema": dict(ranking),
        "top_3": [{"tema": t, "cantidad": c} for t, c in ranking[:3]],
        "concentracion": (
            "alta_tension" if ranking[0][1] > total * 0.3
            else "moderada" if ranking[0][1] > total * 0.15
            else "diversificada"
        ),
    }


# ═══════════════════════════════════════════════════════
#  EMAE DESESTACIONALIZADO
# ═══════════════════════════════════════════════════════

def actividad_emae_ajustada(store: DataStore) -> dict:
    """EMAE con comparacion interanual por mes (evita estacionalidad)."""
    emae = store.serie("emae")
    if not emae or not emae.get("data"):
        return {}

    data = emae["data"]
    puntos = [(d[0], d[1]) for d in data if len(d) == 2 and d[1] is not None]
    if len(puntos) < 13:
        return {}

    # Agrupar por mes
    por_mes = {}
    for fecha, val in puntos:
        mes = fecha[5:7]
        if mes not in por_mes:
            por_mes[mes] = []
        por_mes[mes].append((fecha, val))

    # Para cada mes reciente, comparar con el mismo mes del ano anterior
    comparaciones = []
    for i in range(max(0, len(puntos) - 6), len(puntos)):
        fecha_actual, val_actual = puntos[i]
        mes_actual = fecha_actual[5:7]
        ano_actual = int(fecha_actual[:4])

        # Buscar mismo mes ano anterior
        for fecha_prev, val_prev in puntos:
            if fecha_prev[5:7] == mes_actual and int(fecha_prev[:4]) == ano_actual - 1:
                yoy = _pct_change(val_prev, val_actual)
                comparaciones.append({
                    "fecha": fecha_actual,
                    "actual": round(val_actual, 2),
                    "ano_anterior": round(val_prev, 2),
                    "yoy_pct": yoy,
                })
                break

    if not comparaciones:
        return {}

    # Tendencia YoY (ultimos 3 meses vs 3 anteriores)
    yoys = [c["yoy_pct"] for c in comparaciones if c["yoy_pct"] is not None]
    if len(yoys) >= 4:
        reciente = statistics.mean(yoys[-3:])
        anterior = statistics.mean(yoys[:-3]) if len(yoys) > 3 else yoys[0]
        aceleracion = round(reciente - (anterior if isinstance(anterior, (int, float)) else 0), 2)
    else:
        aceleracion = None

    return {
        "comparaciones": comparaciones,
        "yoy_actual": comparaciones[-1]["yoy_pct"] if comparaciones else None,
        "yoy_promedio": round(statistics.mean(yoys), 2) if yoys else None,
        "aceleracion_yoy": aceleracion,
        "nota": "comparacion mismo mes ano anterior — elimina efecto estacional",
    }


# ═══════════════════════════════════════════════════════
#  DOLAR EURO — Tipo de cambio cruzado
# ═══════════════════════════════════════════════════════

def dolar_euro(store: DataStore) -> dict:
    """Tipo de cambio USD y EUR desde Bluelytics."""
    bl = store.quick.get("bluelytics", {})
    if not bl:
        return {}

    oficial_usd = bl.get("oficial", {})
    blue_usd = bl.get("blue", {})
    oficial_eur = bl.get("oficial_euro", {})
    blue_eur = bl.get("blue_euro", {})

    resultado = {}

    if oficial_usd and blue_usd:
        resultado["usd"] = {
            "oficial": oficial_usd,
            "blue": blue_usd,
            "spread_pct": _pct_change(
                oficial_usd.get("value_avg", 0),
                blue_usd.get("value_avg", 0)
            ),
        }

    if oficial_eur and blue_eur:
        resultado["eur"] = {
            "oficial": oficial_eur,
            "blue": blue_eur,
            "spread_pct": _pct_change(
                oficial_eur.get("value_avg", 0),
                blue_eur.get("value_avg", 0)
            ),
        }

    # EUR/USD implicito
    usd_avg = blue_usd.get("value_avg", 0)
    eur_avg = blue_eur.get("value_avg", 0)
    if usd_avg and eur_avg:
        resultado["eur_usd_implicito"] = round(eur_avg / usd_avg, 4)

    resultado["last_update"] = bl.get("last_update")

    return resultado


# ═══════════════════════════════════════════════════════
#  RIESGO PAIS — Tendencia, volatilidad, CDS
# ═══════════════════════════════════════════════════════

def riesgo_pais_analisis(store: DataStore) -> dict:
    """Analisis completo de riesgo pais + CDS."""
    hist = _load("apis/riesgo_pais_historial.json")
    if not hist:
        return {}

    hist = _sort_by_fecha(hist)
    valores = [_safe_float(d.get("valor")) for d in hist]
    valores = [v for v in valores if v is not None]

    if not valores:
        return {}

    actual = valores[-1]
    hace_7d = valores[-7] if len(valores) >= 7 else valores[0]
    hace_30d = valores[-30] if len(valores) >= 30 else valores[0]
    inicio = valores[0]

    # Volatilidad
    if len(valores) >= 2:
        changes = [abs(valores[i] - valores[i - 1]) for i in range(1, len(valores))]
        vol = round(statistics.stdev(changes), 2) if len(changes) >= 2 else None
    else:
        vol = None

    # Probabilidad implicita de default desde EMBI spread (riesgo pais)
    # Formula: PD = 1 - e^(-spread_bps/10000 * T / (1 - Recovery))
    # Recovery rate tipico: 25-40% para soberanos emergentes
    recovery = 0.35
    prob_default = round((1 - math.exp(-actual / 10000 * 5 / (1 - recovery))) * 100, 2)

    # CDS 5 anos (referencia, unidad puede variar segun fuente BCRA)
    cds = store.bcra_variable("cds_5_anos")
    cds_val = None
    if cds and cds.get("current"):
        cds_val = _safe_float(cds["current"].get("valor"))

    return {
        "actual": actual,
        "var_7d": round(actual - hace_7d, 0) if hace_7d else None,
        "var_30d": round(actual - hace_30d, 0) if hace_30d else None,
        "var_90d": round(actual - inicio, 0),
        "var_7d_pct": _pct_change(hace_7d, actual),
        "var_30d_pct": _pct_change(hace_30d, actual),
        "min_90d": min(valores),
        "max_90d": max(valores),
        "volatilidad": vol,
        "tendencia": "mejorando" if actual < hace_30d else "empeorando" if actual > hace_30d else "estable",
        "cds_5anos_ref": cds_val,
        "probabilidad_default_5a_pct": prob_default,
        "zona": (
            "critica" if actual > 1500
            else "riesgosa" if actual > 1000
            else "moderada" if actual > 700
            else "estable" if actual > 400
            else "baja"
        ),
    }


# ═══════════════════════════════════════════════════════
#  CRAWLING PEG — Velocidad de devaluacion oficial
# ═══════════════════════════════════════════════════════

def crawling_peg(store: DataStore) -> dict:
    """Velocidad del crawling peg: ritmo de devaluacion del dolar oficial."""
    hist = _load("apis/dolar_historial_oficial.json")
    if not hist or len(hist) < 2:
        return {}

    hist = _sort_by_fecha(hist)
    ventas = [(d.get("fecha", ""), _safe_float(d.get("venta"))) for d in hist]
    ventas = [(f, v) for f, v in ventas if v is not None]

    if len(ventas) < 2:
        return {}

    actual = ventas[-1][1]
    inicio = ventas[0][1]
    dias = len(ventas)

    # Tasa diaria
    if inicio > 0 and dias > 0:
        tasa_diaria = ((actual / inicio) ** (1 / dias) - 1) * 100
        tasa_mensual = ((actual / inicio) ** (30 / dias) - 1) * 100
        tasa_anualizada = ((actual / inicio) ** (365 / dias) - 1) * 100
    else:
        tasa_diaria = tasa_mensual = tasa_anualizada = 0

    return {
        "oficial_actual": actual,
        "oficial_90d_atras": inicio,
        "devaluacion_total_pct": _pct_change(inicio, actual),
        "tasa_diaria_pct": round(tasa_diaria, 4),
        "tasa_mensual_pct": round(tasa_mensual, 2),
        "tasa_anualizada_pct": round(tasa_anualizada, 2),
        "dias_analizados": dias,
    }


# ═══════════════════════════════════════════════════════
#  PODER ADQUISITIVO — Erosion del peso
# ═══════════════════════════════════════════════════════

def poder_adquisitivo(store: DataStore) -> dict:
    """Cuanto perdio el peso en poder de compra."""
    inf = inflacion_analisis(store)
    if not inf:
        return {}

    interanual = inf.get("interanual_compuesta", 0)
    acum_3m = inf.get("acumulada_3m", 0)

    # $1000 de hace 12 meses hoy valen...
    valor_1000_12m = round(1000 / (1 + interanual / 100), 2) if interanual else None

    # $1000 de hace 3 meses hoy valen...
    valor_1000_3m = round(1000 / (1 + acum_3m / 100), 2) if acum_3m else None

    # Dias para perder 1% de poder adquisitivo
    ultimo_mes = inf.get("ultimo_mes", 0)
    dias_1pct = round(30 / ultimo_mes, 1) if ultimo_mes > 0 else None

    return {
        "inflacion_interanual_pct": round(interanual, 2),
        "inflacion_3m_pct": round(acum_3m, 2),
        "valor_real_1000_12m": valor_1000_12m,
        "valor_real_1000_3m": valor_1000_3m,
        "perdida_diaria_pct": round(ultimo_mes / 30, 3) if ultimo_mes else None,
        "dias_para_perder_1pct": dias_1pct,
    }


# ═══════════════════════════════════════════════════════
#  INDICE NYX — Score compuesto de riesgo (0-100)
# ═══════════════════════════════════════════════════════

def indice_nyx(store: DataStore, _cache: dict | None = None) -> dict:
    """Indice Nyx: score compuesto de riesgo economico (0-100).
    Mas sofisticado que presion_cambiaria — usa mas variables y ponderacion.
    _cache: dict pre-computado desde reporte_completo para evitar recalcular."""
    score = 50.0
    componentes = {}
    alertas = []

    # Usar cache si disponible, sino calcular
    spreads = _cache.get("sp") if _cache else None
    if spreads is None:
        spreads = dolar_spreads(store)
    rp = _cache.get("rp") if _cache else None
    if rp is None:
        rp = riesgo_pais_analisis(store)
    vel = _cache.get("vel") if _cache else None
    if vel is None:
        vel = dolar_velocidad(store)
    res = _cache.get("res") if _cache else None
    if res is None:
        res = reservas_velocidad(store)
    inf = _cache.get("inf") if _cache else None
    if inf is None:
        inf = inflacion_analisis(store)
    tr = _cache.get("tr") if _cache else None
    if tr is None:
        tr = tasas_reales(store)

    # 1. Brecha cambiaria (peso: 20)
    brecha = spreads.get("blue_vs_oficial", {}).get("brecha_pct")
    if brecha is not None:
        componentes["brecha_cambiaria"] = brecha
        if brecha > 50:
            score += 15
            alertas.append("brecha cambiaria critica (>50%)")
        elif brecha > 30:
            score += 8
        elif brecha > 15:
            score += 3
        elif brecha < 3:
            score -= 8
            alertas.append("brecha casi nula — posible unificacion cambiaria")

    # 2. Riesgo pais (peso: 15)
    rp_val = rp.get("actual")
    if rp_val:
        componentes["riesgo_pais"] = rp_val
        if rp_val > 2000:
            score += 12
            alertas.append("riesgo pais extremo")
        elif rp_val > 1200:
            score += 8
        elif rp_val > 800:
            score += 3
        elif rp_val < 500:
            score -= 8

    # 3. Volatilidad blue (peso: 10)
    blue_vol = vel.get("blue", {}).get("volatilidad_diaria_pct")
    if blue_vol is not None:
        componentes["volatilidad_blue"] = blue_vol
        if blue_vol > 2:
            score += 8
            alertas.append("alta volatilidad en dolar blue")
        elif blue_vol > 1:
            score += 4
        elif blue_vol < 0.3:
            score -= 3

    # 4. Reservas (peso: 12)
    if res:
        usd_dia = res.get("usd_por_dia_7d", 0)
        componentes["reservas_usd_dia"] = usd_dia
        if usd_dia < -100:
            score += 10
            alertas.append("reservas cayendo fuerte")
        elif usd_dia < -30:
            score += 5
        elif usd_dia > 50:
            score -= 5

    # 5. Inflacion tendencia (peso: 10)
    if inf:
        aceleracion = inf.get("aceleracion")
        componentes["inflacion_tendencia"] = inf.get("tendencia")
        if aceleracion and aceleracion > 1:
            score += 8
            alertas.append("inflacion acelerando")
        elif aceleracion and aceleracion > 0.3:
            score += 3
        elif aceleracion and aceleracion < -0.5:
            score -= 5

    # 6. Tasa real (peso: 8)
    badlar = tr.get("tasa_badlar", {})
    if badlar:
        real = badlar.get("tasa_real_anual", 0)
        componentes["tasa_real_badlar"] = real
        if real < -10:
            score += 6
        elif real < 0:
            score += 3
        elif real > 5:
            score -= 4

    # 7. Default probability from EMBI (peso: 8)
    prob_default = rp.get("probabilidad_default_5a_pct")
    if prob_default is not None:
        componentes["prob_default_5a"] = prob_default
        if prob_default > 50:
            score += 8
            alertas.append("probabilidad de default elevada")
        elif prob_default > 30:
            score += 4
        elif prob_default < 10:
            score -= 3

    # 8. Actividad economica (peso: 7)
    emae = actividad_emae(store)
    if emae:
        yoy = emae.get("var_interanual_pct")
        componentes["emae_yoy"] = yoy
        if yoy and yoy < -5:
            score += 6
            alertas.append("recesion economica")
        elif yoy and yoy < -2:
            score += 3
        elif yoy and yoy > 3:
            score -= 3

    # 9. Sentiment social (peso: 5)
    sent = sentiment_social(store)
    if sent and sent.get("ratio_pos_neg") is not None:
        ratio = sent["ratio_pos_neg"]
        componentes["sentiment_ratio"] = ratio
        if ratio < 0.5:
            score += 4
            alertas.append("sentiment social muy negativo")
        elif ratio < 0.7:
            score += 2
        elif ratio > 1.5:
            score -= 3

    # 10. Core vs headline inflation (peso: 4)
    cvh = inflacion_core_vs_headline(store)
    if cvh and cvh.get("spread_actual_pp") is not None:
        spread = cvh["spread_actual_pp"]
        componentes["inflacion_core_spread"] = spread
        if spread > 0.5:
            score += 3
            alertas.append("inflacion nucleo por encima de headline — presion subyacente")
        elif spread < -0.5:
            score -= 1

    # Clamp
    score = max(0, min(100, score))

    # Nivel textual
    if score >= 80:
        nivel = "critico"
    elif score >= 65:
        nivel = "alto"
    elif score >= 45:
        nivel = "moderado"
    elif score >= 25:
        nivel = "bajo"
    else:
        nivel = "muy_bajo"

    return {
        "score": round(score, 1),
        "nivel": nivel,
        "componentes": componentes,
        "alertas": alertas,
        "variables_usadas": len(componentes),
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ═══════════════════════════════════════════════════════
#  REPORTE COMPLETO — Todo en uno para el agente
# ═══════════════════════════════════════════════════════

def reporte_completo(store: DataStore) -> dict:
    """Genera reporte completo de analisis — ideal para el agente Nyx.
    Usa cache interno para evitar recalcular dolar_velocidad y otros."""
    # Pre-computar datos caros una sola vez
    _vel = dolar_velocidad(store)
    _sp = dolar_spreads(store)
    _inf = inflacion_analisis(store)
    _rp = riesgo_pais_analisis(store)
    _tr = tasas_reales(store)
    _res = reservas_velocidad(store)

    return {
        "indice_nyx": indice_nyx(store, _cache={
            "vel": _vel, "sp": _sp, "inf": _inf, "rp": _rp, "tr": _tr, "res": _res,
        }),
        "dolar": {
            "velocidad": _vel,
            "spreads": _sp,
            "blend": dolar_blend(store),
            "crawling_peg": crawling_peg(store),
            "implicito": dolar_implicito(store),
            "euro": dolar_euro(store),
        },
        "inflacion": {
            "actual": _inf,
            "core_vs_headline": inflacion_core_vs_headline(store),
            "extendida": inflacion_extendida(store),
        },
        "actividad": {
            "emae": actividad_emae(store),
            "desestacionalizado": actividad_emae_ajustada(store),
        },
        "tasas": {
            "reales": _tr,
            "politica_monetaria": tasa_politica(store),
            "carry_trade": carry_trade(store),
            "carry_multi": carry_trade_multi(store),
        },
        "reservas": _res,
        "riesgo_pais": _rp,
        "monetario": {
            "expansion": expansion_monetaria(store),
            "depositos_ratio": depositos_ratio(store),
            "depositos_tendencia": depositos_tendencia(store),
            "multiplicador": multiplicador_monetario(store),
        },
        "social": {
            "sentiment": sentiment_social(store),
            "noticias_volumen": noticias_volumen(store),
        },
        "poder_adquisitivo": poder_adquisitivo(store),
    }


# ═══════════════════════════════════════════════════════
#  RESUMEN EJECUTIVO — Texto para humanos
# ═══════════════════════════════════════════════════════

def resumen_ejecutivo(store: DataStore) -> str:
    """Genera un resumen ejecutivo en texto para mostrar o alimentar al agente."""
    # Computar todo una sola vez
    vel = dolar_velocidad(store)
    sp = dolar_spreads(store)
    inf = inflacion_analisis(store)
    rp = riesgo_pais_analisis(store)
    tr = tasas_reales(store)
    res = reservas_velocidad(store)

    nyx = indice_nyx(store, _cache={"vel": vel, "sp": sp, "inf": inf, "rp": rp, "tr": tr, "res": res})
    impl = dolar_implicito(store)
    ct = carry_trade(store)
    cp = crawling_peg(store)
    emae = actividad_emae(store)
    cvh = inflacion_core_vs_headline(store)
    tp = tasa_politica(store)
    sent = sentiment_social(store)

    lines = []
    lines.append(f"INDICE NYX: {nyx['score']}/100 ({nyx['nivel'].upper()}) [{nyx.get('variables_usadas', '?')} variables]")

    if nyx.get("alertas"):
        for a in nyx["alertas"]:
            lines.append(f"  ! {a}")

    lines.append("")

    # Dolar
    blue = vel.get("blue", {})
    if blue:
        lines.append(f"DOLAR BLUE: ${blue.get('actual', '?')} | 7d: {blue.get('var_7d_pct', '?')}% | 30d: {blue.get('var_30d_pct', '?')}% | vol: {blue.get('volatilidad_diaria_pct', '?')}%")

    brecha = sp.get("blue_vs_oficial", {})
    if brecha:
        lines.append(f"BRECHA: {brecha.get('brecha_pct', '?')}%")

    conv = sp.get("convergencia", {})
    if conv:
        lines.append(f"CONVERGENCIA: dispersion {conv.get('dispersion_pct', '?')}% ({conv.get('nivel', '?')})")

    if impl:
        lines.append(f"DOLAR IMPLICITO: ${impl.get('dolar_implicito_base', '?')} (base) | ratio blue/impl: {impl.get('ratio_blue_vs_implicito', '?')}")

    if cp:
        lines.append(f"CRAWLING PEG: {cp.get('tasa_mensual_pct', '?')}% mensual ({cp.get('tasa_anualizada_pct', '?')}% anualizado)")

    lines.append("")

    # Inflacion
    if inf:
        lines.append(f"INFLACION: {inf.get('ultimo_mes', '?')}% mensual | {inf.get('interanual_compuesta', '?')}% interanual | tendencia: {inf.get('tendencia', '?')}")

    if cvh and cvh.get("spread_actual_pp") is not None:
        lines.append(f"  core vs headline: {cvh['spread_actual_pp']:+.2f}pp ({cvh.get('interpretacion', '')})")

    # Tasas
    if tp and tp.get("pases_pasivos"):
        lines.append(f"TASA POLITICA: pases pasivos {tp.get('pases_pasivos', '?')}% | BADLAR {tp.get('badlar', '?')}% | spread {tp.get('spread_pases_badlar_pp', '?')}pp")

    # EMAE
    if emae:
        lines.append(f"ACTIVIDAD (EMAE): {emae.get('var_interanual_pct', '?')}% YoY | estado: {emae.get('estado', '?')}")

    # Riesgo pais
    if rp:
        lines.append(f"RIESGO PAIS: {rp.get('actual', '?')} | 30d: {rp.get('var_30d', '?')} pts | zona: {rp.get('zona', '?')}")
        if rp.get("probabilidad_default_5a_pct"):
            lines.append(f"  prob default 5a: {rp['probabilidad_default_5a_pct']}%")

    # Reservas
    if res:
        lines.append(f"RESERVAS: USD {res.get('actual_usd_mm', '?')}MM | {res.get('usd_por_dia_7d', '?')} USD/dia (7d) | {res.get('tendencia', '?')}")

    # Carry trade
    if ct and ct.get("mejor_plazo_fijo"):
        lines.append(f"CARRY TRADE: {ct.get('ganancia_carry_mensual_pct', '?')}% mensual | {'POSITIVO' if ct.get('carry_positivo') else 'NEGATIVO'}")

    # Sentiment
    if sent and sent.get("ratio_pos_neg") is not None:
        lines.append(f"SENTIMENT SOCIAL: {sent.get('tono', '?')} (ratio {sent['ratio_pos_neg']}) | {sent.get('total_tweets', '?')} tweets")

    return "\n".join(lines)
