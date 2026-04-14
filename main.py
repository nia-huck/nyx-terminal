"""Nyx Terminal — Entry point.

Carga la data, calcula senales, clasifica noticias y muestra resumen.
Para la API web: python api.py
"""

from __future__ import annotations

import json
from core.store import DataStore
from core.signals import all_signals
from core.classifier import classify_all


def main():
    print("=" * 60)
    print("  NYX TERMINAL — Mapa de Riesgo Economico Argentina")
    print("=" * 60)

    # 1. Cargar data
    print("\n[1] Cargando DataStore...")
    store = DataStore()
    summary = store.summary()
    print(f"    Archivos: {summary['total_files']}")
    print(f"    Tamano: {summary['total_size_mb']} MB")
    print(f"    Categorias: {', '.join(summary['categories'])}")

    if summary["dolar_blue"]:
        db = summary["dolar_blue"]
        print(f"    Dolar Blue: compra={db.get('compra')} venta={db.get('venta')}")

    if summary["riesgo_pais"]:
        rp = summary["riesgo_pais"]
        print(f"    Riesgo Pais: {rp.get('v', rp.get('valor', '?'))}")

    # 2. Senales derivadas
    print("\n[2] Calculando senales...")
    signals = all_signals(store)

    brecha = signals.get("brecha_cambiaria")
    if brecha:
        print(f"    Brecha cambiaria: {brecha['brecha_pct']}%")

    tr = signals.get("tasa_real")
    if tr:
        print(f"    Tasa real: {tr['tasa_real']}% (BADLAR {tr['badlar']}% - Inflacion {tr['inflacion_12m']}%)")

    res = signals.get("tendencia_reservas")
    if res:
        print(f"    Reservas: {res['tendencia']} ({res['cambio_pct']}% en {res['dias']}d)")

    pc = signals.get("presion_cambiaria")
    if pc:
        print(f"    Presion cambiaria: {pc['score']}/100 ({pc['nivel']})")

    # 3. Clasificar noticias
    print("\n[3] Clasificando noticias...")
    noticias = store.noticias()
    print(f"    Total noticias: {len(noticias)}")

    if noticias:
        events = classify_all(noticias)
        print(f"    Eventos clasificados: {len(events)}")

        # Contar por tipo
        tipos = {}
        for e in events:
            t = e["tipo"]
            tipos[t] = tipos.get(t, 0) + 1
        for t, c in sorted(tipos.items(), key=lambda x: -x[1]):
            print(f"      {t}: {c}")

        # Top 5 mas urgentes
        print("\n    Top 5 eventos mas urgentes:")
        for e in events[:5]:
            print(f"      [{e['urgencia']}/10] [{e['tipo']}] {e['titulo'][:80]}")

    # 4. Info adicional
    tweets = store.tweets()
    reddit = store.reddit()
    trends = store.trends()
    print(f"\n[4] Data adicional:")
    print(f"    Tweets: {len(tweets)}")
    print(f"    Reddit posts: {len(reddit)}")
    print(f"    Google Trends: {len(trends)} terminos")

    print("\n" + "=" * 60)
    print("  Listo. Usa 'python api.py' para levantar la API.")
    print("=" * 60)


if __name__ == "__main__":
    main()
