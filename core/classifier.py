"""Nyx Terminal — Clasificador de noticias en eventos tipados."""

from __future__ import annotations

import re
from datetime import datetime

# Palabras clave por tipo de evento
KEYWORDS = {
    "sindical": [
        "paro", "huelga", "sindicato", "gremio", "paritaria", "cgt", "camioneros",
        "protesta", "corte", "movilizacion", "medida de fuerza", "reclamo salarial",
    ],
    "regulatorio": [
        "bcra", "resolucion", "comunicacion", "normativa", "decreto", "cepo",
        "tipo de cambio", "regulacion", "boletin oficial", "afip", "arca",
    ],
    "economico": [
        "dolar", "inflacion", "riesgo pais", "merval", "bonos", "tasa",
        "reservas", "devaluacion", "cotizacion", "brecha", "plazo fijo",
        "cedear", "rendimiento", "emae", "pbi", "exportacion", "importacion",
    ],
    "politico": [
        "congreso", "ley", "presupuesto", "milei", "gobierno", "oposicion",
        "elecciones", "fiscal", "impuesto", "senado", "diputados",
    ],
    "climatico": [
        "sequia", "inundacion", "cosecha", "clima", "helada", "tormenta",
        "incendio", "granizo", "emergencia agropecuaria",
    ],
}

# Sectores asociados a cada tipo
SECTOR_MAP = {
    "sindical": ["logistica", "trabajo"],
    "regulatorio": ["finanzas", "regulacion"],
    "economico": ["finanzas", "mercado"],
    "politico": ["gobierno", "fiscal"],
    "climatico": ["agro", "energia"],
}

# Activos afectados por tipo
ACTIVOS_MAP = {
    "sindical": ["logistica", "consumo"],
    "regulatorio": ["dolar", "bonos", "acciones_bancarias"],
    "economico": ["bonos_soberanos", "acciones", "dolar"],
    "politico": ["bonos_soberanos", "riesgo_pais"],
    "climatico": ["agro", "soja", "exportaciones"],
}

# ── Coordenadas por ubicación ──────────────────────────────────
UBICACION_COORDS = {
    # Provincias argentinas
    "CABA":                (-34.6037, -58.3816),
    "Buenos Aires":        (-34.9215, -57.9545),
    "Córdoba":             (-31.4201, -64.1888),
    "Santa Fe":            (-32.9468, -60.6393),
    "Rosario":             (-32.9442, -60.6505),
    "Mendoza":             (-32.8895, -68.8458),
    "Tucumán":             (-26.8083, -65.2176),
    "Salta":               (-24.7821, -65.4232),
    "Entre Ríos":          (-31.7413, -60.5115),
    "Misiones":            (-27.3671, -55.8961),
    "Chaco":               (-27.4514, -58.9867),
    "Corrientes":          (-27.4692, -58.8306),
    "Santiago del Estero":  (-27.7834, -64.2642),
    "San Juan":            (-31.5375, -68.5364),
    "Jujuy":               (-24.1858, -65.2995),
    "Río Negro":           (-38.9516, -68.0591),
    "Neuquén":             (-38.9516, -68.0591),
    "Formosa":             (-26.1775, -58.1781),
    "Chubut":              (-43.3002, -65.1023),
    "San Luis":            (-33.2962, -66.3356),
    "Catamarca":           (-28.4696, -65.7852),
    "La Rioja":            (-29.4131, -66.8559),
    "La Pampa":            (-36.6167, -64.2833),
    "Santa Cruz":          (-51.6226, -69.2181),
    "Tierra del Fuego":    (-54.8019, -68.3030),
    # Países / ciudades internacionales
    "Estados Unidos":      (38.9, -77.0),
    "Brasil":              (-15.7939, -47.8828),
    "China":               (39.9042, 116.4074),
    "Rusia":               (55.7558, 37.6173),
    "Japón":               (35.6762, 139.6503),
    "Unión Europea":       (50.8503, 4.3517),
    "Alemania":            (52.52, 13.405),
    "Francia":             (48.8566, 2.3522),
    "Reino Unido":         (51.5074, -0.1278),
    "México":              (19.4326, -99.1332),
    "Chile":               (-33.4489, -70.6693),
    "Uruguay":             (-34.9011, -56.1645),
    "Paraguay":            (-25.2637, -57.5759),
    "Bolivia":             (-16.4897, -68.1193),
    "Colombia":            (4.711, -74.0721),
    "Venezuela":           (10.4806, -66.9036),
    "Perú":                (-12.0464, -77.0428),
    "FMI":                 (38.9, -77.0),
    "Wall Street":         (40.7069, -74.0089),
    "Ucrania":             (50.4501, 30.5234),
    "Israel":              (31.7683, 35.2137),
    "India":               (28.6139, 77.209),
    "Corea del Sur":       (37.5665, 126.978),
    "Australia":           (-33.8688, 151.2093),
    "Arabia Saudita":      (24.7136, 46.6753),
}

# ── Keywords → ubicación (de más específico a menos) ───────────
# Tuplas (keyword, ubicación) — se buscan en orden, el primero que matchea gana.
# Las frases más largas van primero para evitar falsos positivos.
_LOCATION_RULES: list[tuple[str, str]] = [
    # Lugares específicos dentro de provincias
    ("vaca muerta", "Neuquén"),
    ("gran rosario", "Rosario"),
    ("puerto madero", "CABA"),
    ("microcentro", "CABA"),
    ("casa rosada", "CABA"),
    ("plaza de mayo", "CABA"),
    ("la matanza", "Buenos Aires"),
    ("gran buenos aires", "Buenos Aires"),
    ("provincia de buenos aires", "Buenos Aires"),
    ("conurbano bonaerense", "Buenos Aires"),
    ("conurbano", "Buenos Aires"),
    ("mar del plata", "Buenos Aires"),
    ("bahía blanca", "Buenos Aires"),
    ("bahia blanca", "Buenos Aires"),
    ("la plata", "Buenos Aires"),
    ("comodoro rivadavia", "Chubut"),
    ("ushuaia", "Tierra del Fuego"),
    ("bariloche", "Río Negro"),
    ("san carlos de bariloche", "Río Negro"),
    ("puerto iguazú", "Misiones"),
    ("puerto iguazu", "Misiones"),
    ("resistencia", "Chaco"),
    ("posadas", "Misiones"),
    ("san salvador de jujuy", "Jujuy"),
    ("san miguel de tucumán", "Tucumán"),
    ("san miguel de tucuman", "Tucumán"),
    ("san fernando del valle", "Catamarca"),
    ("río gallegos", "Santa Cruz"),
    ("rio gallegos", "Santa Cruz"),
    ("rawson", "Chubut"),
    ("trelew", "Chubut"),
    ("paraná", "Entre Ríos"),
    ("parana", "Entre Ríos"),
    ("concordia", "Entre Ríos"),
    ("rafaela", "Santa Fe"),
    ("reconquista", "Santa Fe"),
    ("san rafael", "Mendoza"),
    # Provincias (nombre completo)
    ("tierra del fuego", "Tierra del Fuego"),
    ("santiago del estero", "Santiago del Estero"),
    ("entre ríos", "Entre Ríos"),
    ("entre rios", "Entre Ríos"),
    ("río negro", "Río Negro"),
    ("rio negro", "Río Negro"),
    ("la pampa", "La Pampa"),
    ("la rioja", "La Rioja"),
    ("san juan", "San Juan"),
    ("san luis", "San Luis"),
    ("santa cruz", "Santa Cruz"),
    ("santa fe", "Santa Fe"),
    ("córdoba", "Córdoba"),
    ("cordoba", "Córdoba"),
    ("mendoza", "Mendoza"),
    ("tucumán", "Tucumán"),
    ("tucuman", "Tucumán"),
    ("neuquén", "Neuquén"),
    ("neuquen", "Neuquén"),
    ("salta", "Salta"),
    ("jujuy", "Jujuy"),
    ("chubut", "Chubut"),
    ("formosa", "Formosa"),
    ("misiones", "Misiones"),
    ("corrientes", "Corrientes"),
    ("catamarca", "Catamarca"),
    ("chaco", "Chaco"),
    ("rosario", "Rosario"),
    ("buenos aires", "Buenos Aires"),
    ("patagonia", "Río Negro"),
    ("litoral", "Santa Fe"),
    ("noa", "Salta"),
    ("nea", "Chaco"),
    ("cuyo", "Mendoza"),
    # Instituciones nacionales → CABA
    ("congreso de la nación", "CABA"),
    ("congreso nacional", "CABA"),
    ("banco central", "CABA"),
    ("ministerio de economía", "CABA"),
    ("ministerio de economia", "CABA"),
    ("casa de gobierno", "CABA"),
    ("bolsa de comercio", "CABA"),
    ("plaza de mayo", "CABA"),
    # Internacionales — frases largas primero
    ("estados unidos", "Estados Unidos"),
    ("wall street", "Wall Street"),
    ("reserva federal", "Estados Unidos"),
    ("fed de eeuu", "Estados Unidos"),
    ("corea del sur", "Corea del Sur"),
    ("arabia saudita", "Arabia Saudita"),
    ("unión europea", "Unión Europea"),
    ("union europea", "Unión Europea"),
    ("reino unido", "Reino Unido"),
    ("ee.uu.", "Estados Unidos"),
    ("ee.uu", "Estados Unidos"),
    ("eeuu", "Estados Unidos"),
    ("trump", "Estados Unidos"),
    ("biden", "Estados Unidos"),
    ("washington", "Estados Unidos"),
    ("nueva york", "Wall Street"),
    ("new york", "Wall Street"),
    ("brasil", "Brasil"),
    ("brasilia", "Brasil"),
    ("lula", "Brasil"),
    ("china", "China"),
    ("beijing", "China"),
    ("pekín", "China"),
    ("pekin", "China"),
    ("xi jinping", "China"),
    ("rusia", "Rusia"),
    ("moscú", "Rusia"),
    ("moscu", "Rusia"),
    ("putin", "Rusia"),
    ("japón", "Japón"),
    ("japon", "Japón"),
    ("tokio", "Japón"),
    ("alemania", "Alemania"),
    ("berlín", "Alemania"),
    ("berlin", "Alemania"),
    ("francia", "Francia"),
    ("paris", "Francia"),
    ("londres", "Reino Unido"),
    ("méxico", "México"),
    ("mexico", "México"),
    ("chile", "Chile"),
    ("santiago de chile", "Chile"),
    ("uruguay", "Uruguay"),
    ("montevideo", "Uruguay"),
    ("paraguay", "Paraguay"),
    ("asunción", "Paraguay"),
    ("bolivia", "Bolivia"),
    ("la paz", "Bolivia"),
    ("colombia", "Colombia"),
    ("bogotá", "Colombia"),
    ("bogota", "Colombia"),
    ("venezuela", "Venezuela"),
    ("caracas", "Venezuela"),
    ("perú", "Perú"),
    ("peru", "Perú"),
    ("lima", "Perú"),
    ("fmi", "FMI"),
    ("fondo monetario", "FMI"),
    ("ucrania", "Ucrania"),
    ("kiev", "Ucrania"),
    ("israel", "Israel"),
    ("gaza", "Israel"),
    ("india", "India"),
    ("nueva delhi", "India"),
    ("australia", "Australia"),
]


def _detect_ubicacion(text: str) -> str | None:
    """Detecta ubicación mencionada en el texto.

    Retorna None si no se encuentra ninguna referencia geográfica clara.
    """
    text_lower = text.lower()
    for keyword, ubicacion in _LOCATION_RULES:
        if keyword in text_lower:
            return ubicacion
    return None


_next_id = 2000


def _gen_id() -> int:
    global _next_id
    _next_id += 1
    return _next_id


def classify_text(text: str) -> tuple[str, int]:
    """Clasifica un texto y devuelve (tipo, urgencia)."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for tipo, keywords in KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            scores[tipo] = count

    if not scores:
        return "informativo", 3

    best = max(scores, key=scores.get)
    max_score = scores[best]
    urgencia = min(10, 3 + max_score * 2)
    return best, urgencia


def news_to_event(item: dict) -> dict:
    """Convierte un item de noticias al formato nyx-event."""
    titulo = item.get("titulo", item.get("title", ""))
    resumen = item.get("resumen", item.get("text", item.get("description", "")))
    texto_completo = f"{titulo} {resumen}"

    tipo, urgencia = classify_text(texto_completo)

    ubicacion = _detect_ubicacion(texto_completo)
    if ubicacion:
        lat, lon = UBICACION_COORDS.get(ubicacion, (None, None))
    else:
        lat, lon = None, None

    return {
        "id": _gen_id(),
        "titulo": titulo[:120],
        "tipo": tipo,
        "sector": SECTOR_MAP.get(tipo, ["general"]),
        "urgencia": urgencia,
        "provincia": ubicacion,
        "lat": lat,
        "lon": lon,
        "fecha": item.get("fecha", item.get("date", datetime.now().strftime("%Y-%m-%d"))),
        "resumen": resumen[:500] if resumen else titulo,
        "fuente": item.get("fuente", item.get("source", "")),
        "fuente_url": item.get("link", item.get("url", "")),
        "activos_afectados": ACTIVOS_MAP.get(tipo, []),
        "horizonte_impacto": "24h" if urgencia >= 7 else "1 semana",
    }


def classify_all(news_items: list[dict]) -> list[dict]:
    """Clasifica una lista de noticias en eventos."""
    events = []
    for item in news_items:
        ev = news_to_event(item)
        events.append(ev)
    # Ordenar por urgencia descendente
    events.sort(key=lambda e: e["urgencia"], reverse=True)
    return events
