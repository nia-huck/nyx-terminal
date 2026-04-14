"""Nyx Terminal — Diaricat Live consumer client.

Connects to Diaricat Live's SSE endpoint and converts live transcript alerts
into the standard nyx-events format for display in the terminal dashboard.

Usage:
    python nyx_diaricat_client.py                          # listen to all sessions
    python nyx_diaricat_client.py --session live-0001      # specific session
    python nyx_diaricat_client.py --start "https://..."    # start a new stream + listen
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
from datetime import datetime
from pathlib import Path

import httpx

DIARICAT_LIVE_URL = "http://127.0.0.1:8766"
NYX_EVENTS_FILE = Path(__file__).parent / "nyx-live-events.json"

# Maps Diaricat sectors to nyx-events "tipo"
SECTOR_TO_TIPO = {
    "finanzas": "economico",
    "economia": "economico",
    "mercado": "economico",
    "sindical": "sindical",
    "energia": "regulatorio",
    "agro": "economico",
    "custom": "informativo",
}

# Maps sectors to likely affected assets
SECTOR_TO_ACTIVOS = {
    "finanzas": ["dolar", "bonos", "acciones_bancarias"],
    "economia": ["bonos_soberanos", "acciones"],
    "mercado": ["acciones", "bonos_soberanos", "cedears"],
    "sindical": ["logistica", "consumo"],
    "energia": ["YPF", "tarifas", "energia"],
    "agro": ["soja", "agro", "exportaciones"],
}


class NyxEventCounter:
    """Auto-incrementing ID for nyx events."""

    def __init__(self, start: int = 1000):
        self._id = start

    def next(self) -> int:
        self._id += 1
        return self._id


counter = NyxEventCounter()


def alert_to_nyx_event(alert: dict) -> dict:
    """Convert a Diaricat Live alert event to the nyx-events-demo.json format."""
    sector = alert.get("sector", "custom")
    keyword = alert.get("keyword", "")
    text = alert.get("text", "")

    # Build a title from the keyword + context
    titulo = text[:100].strip()
    if len(text) > 100:
        titulo = titulo.rsplit(" ", 1)[0] + "..."

    return {
        "id": counter.next(),
        "titulo": f"[LIVE] {keyword.upper()}: {titulo}",
        "tipo": SECTOR_TO_TIPO.get(sector, "informativo"),
        "sector": [sector],
        "urgencia": alert.get("urgency", 5),
        "provincia": "CABA",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "resumen": text,
        "fuente": "Diaricat Live",
        "fuente_url": "",
        "activos_afectados": SECTOR_TO_ACTIVOS.get(sector, []),
        "horizonte_impacto": "inmediato",
        "_meta": {
            "source": "diaricat-live",
            "session_id": alert.get("session_id", ""),
            "keyword": keyword,
            "detected_at": alert.get("ts", ""),
        },
    }


def transcript_to_nyx_event(transcript: dict) -> dict:
    """Convert a transcript event to a lightweight nyx event (for full feed mode)."""
    text = transcript.get("text", "")
    return {
        "id": counter.next(),
        "titulo": f"[TRANSCRIPCION] {text[:80]}",
        "tipo": "informativo",
        "sector": ["media"],
        "urgencia": 1,
        "provincia": "CABA",
        "lat": -34.6037,
        "lon": -58.3816,
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "resumen": text,
        "fuente": "Diaricat Live",
        "fuente_url": "",
        "activos_afectados": [],
        "horizonte_impacto": "inmediato",
    }


def start_stream(url: str, language: str = "es") -> str | None:
    """POST to Diaricat Live to start a new stream session."""
    try:
        resp = httpx.post(
            f"{DIARICAT_LIVE_URL}/v1/stream/start",
            json={"url": url, "language": language},
            timeout=60,  # yt-dlp resolve can take a bit
        )
        resp.raise_for_status()
        data = resp.json()
        session_id = data["session_id"]
        print(f"  Stream iniciado: {session_id}")
        return session_id
    except httpx.HTTPError as exc:
        print(f"  Error iniciando stream: {exc}")
        return None


def listen(session_id: str | None = None, alerts_only: bool = True) -> None:
    """Connect to SSE and print/save events as they arrive."""
    if session_id:
        sse_url = f"{DIARICAT_LIVE_URL}/v1/stream/events/{session_id}"
    else:
        sse_url = f"{DIARICAT_LIVE_URL}/v1/stream/events"

    print(f"  Conectando a {sse_url} ...")
    print(f"  Modo: {'solo alertas' if alerts_only else 'todo (transcripcion + alertas)'}")
    print(f"  Guardando eventos en: {NYX_EVENTS_FILE}")
    print("  Ctrl+C para detener\n")

    live_events: list[dict] = []

    # Load existing events if file exists
    if NYX_EVENTS_FILE.exists():
        try:
            live_events = json.loads(NYX_EVENTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    try:
        with httpx.stream("GET", sse_url, timeout=None) as response:
            buffer = ""
            event_type = ""

            for line in response.iter_lines():
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    data_str = line[5:].strip()
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    nyx_event = None

                    if event_type == "alert":
                        nyx_event = alert_to_nyx_event(data)
                        urgency = data.get("urgency", 0)
                        marker = "!!" if urgency >= 8 else "!"
                        print(
                            f"  {marker} ALERTA [{data.get('sector', '?')}] "
                            f"u={urgency} | {data.get('keyword', '?')}: "
                            f"{data.get('text', '')[:120]}"
                        )

                    elif event_type == "transcript" and not alerts_only:
                        nyx_event = transcript_to_nyx_event(data)
                        print(f"     {data.get('text', '')[:120]}")

                    elif event_type == "status":
                        up = data.get("uptime_s", 0)
                        segs = data.get("segments_count", 0)
                        alts = data.get("alerts_count", 0)
                        print(
                            f"  ~ heartbeat | uptime={up:.0f}s "
                            f"segments={segs} alerts={alts}"
                        )

                    elif event_type == "error":
                        print(f"  ERROR: {data.get('message', '?')}")

                    # Persist alert events to file
                    if nyx_event and event_type == "alert":
                        live_events.append(nyx_event)
                        NYX_EVENTS_FILE.write_text(
                            json.dumps(live_events, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )

    except httpx.ReadError:
        print("\n  Conexion cerrada por el servidor.")
    except KeyboardInterrupt:
        print(f"\n  Detenido. {len(live_events)} alertas guardadas en {NYX_EVENTS_FILE.name}")


def status() -> None:
    """Print current Diaricat Live sessions."""
    try:
        resp = httpx.get(f"{DIARICAT_LIVE_URL}/v1/stream/status", timeout=5)
        resp.raise_for_status()
        sessions = resp.json().get("sessions", [])
        if not sessions:
            print("  No hay sesiones activas.")
            return
        for s in sessions:
            print(
                f"  {s['session_id']} | {s['state']} | "
                f"uptime={s['uptime_s']:.0f}s | "
                f"segments={s['segments_count']} | "
                f"alerts={s['alerts_count']} | "
                f"{s['url'][:60]}"
            )
    except httpx.HTTPError as exc:
        print(f"  Error conectando a Diaricat Live: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Nyx Terminal — Diaricat Live consumer",
    )
    parser.add_argument("--start", type=str, help="YouTube/stream URL to start transcribing")
    parser.add_argument("--session", type=str, help="Session ID to listen to")
    parser.add_argument("--lang", type=str, default="es", help="Language hint (default: es)")
    parser.add_argument("--all", action="store_true", help="Show transcripts too, not just alerts")
    parser.add_argument("--status", action="store_true", help="Show active sessions and exit")
    parser.add_argument(
        "--base-url", type=str, default=DIARICAT_LIVE_URL, help="Diaricat Live base URL"
    )
    args = parser.parse_args()

    global DIARICAT_LIVE_URL
    DIARICAT_LIVE_URL = args.base_url

    print("=" * 60)
    print("  NYX TERMINAL — Diaricat Live Monitor")
    print("=" * 60)

    if args.status:
        status()
        return

    session_id = args.session

    if args.start:
        print(f"\n  Iniciando stream: {args.start}")
        session_id = start_stream(args.start, args.lang)
        if not session_id:
            sys.exit(1)

    print()
    status()
    print()

    listen(session_id=session_id, alerts_only=not args.all)


if __name__ == "__main__":
    main()
