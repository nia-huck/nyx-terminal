"""
Diaricat Live — servicio interno de Nyx Terminal
Implementa la API Diaricat Live en puerto 8766
Usa youtube-transcript-api para extraer captions de YouTube
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ── Logging ──────────────────────────────────────────────────────────────
LOG_FILE = Path(__file__).parent / "diaricat.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("diaricat")

# ── Keywords por defecto ─────────────────────────────────────────────────
DEFAULT_KEYWORDS: dict[str, dict] = {
    "dolar":          {"sector": "finanzas",  "urgency": 7},
    "blue":           {"sector": "finanzas",  "urgency": 8},
    "cepo":           {"sector": "finanzas",  "urgency": 8},
    "inflacion":      {"sector": "economia",  "urgency": 7},
    "inflación":      {"sector": "economia",  "urgency": 7},
    "bcra":           {"sector": "finanzas",  "urgency": 6},
    "reservas":       {"sector": "finanzas",  "urgency": 7},
    "devaluacion":    {"sector": "finanzas",  "urgency": 9},
    "devaluación":    {"sector": "finanzas",  "urgency": 9},
    "tipo de cambio": {"sector": "finanzas",  "urgency": 7},
    "mep":            {"sector": "finanzas",  "urgency": 7},
    "ccl":            {"sector": "finanzas",  "urgency": 7},
    "riesgo pais":    {"sector": "economia",  "urgency": 7},
    "riesgo país":    {"sector": "economia",  "urgency": 7},
    "indec":          {"sector": "economia",  "urgency": 5},
    "huelga":         {"sector": "sindical",  "urgency": 8},
    "paro":           {"sector": "sindical",  "urgency": 8},
    "marcha":         {"sector": "sindical",  "urgency": 6},
    "fmi":            {"sector": "economia",  "urgency": 8},
    "bono":           {"sector": "finanzas",  "urgency": 6},
    "deuda":          {"sector": "economia",  "urgency": 7},
    "retenciones":    {"sector": "agro",      "urgency": 7},
    "soja":           {"sector": "agro",      "urgency": 5},
    "tarifas":        {"sector": "energia",   "urgency": 6},
    "ypf":            {"sector": "energia",   "urgency": 6},
    "crisis":         {"sector": "economia",  "urgency": 9},
    "default":        {"sector": "finanzas",  "urgency": 10},
    "acuerdo":        {"sector": "economia",  "urgency": 6},
    "exportacion":    {"sector": "comercio",  "urgency": 5},
    "exportación":    {"sector": "comercio",  "urgency": 5},
    "brecha":         {"sector": "finanzas",  "urgency": 7},
    "crawling":       {"sector": "finanzas",  "urgency": 6},
    "licitar":        {"sector": "finanzas",  "urgency": 6},
    "licitacion":     {"sector": "finanzas",  "urgency": 6},
    "licitación":     {"sector": "finanzas",  "urgency": 6},
}

# Keywords mutables en runtime
keywords: dict[str, dict] = dict(DEFAULT_KEYWORDS)

# Sesiones activas
sessions: dict[str, dict] = {}


# ── Helpers ──────────────────────────────────────────────────────────────
def extract_video_id(url: str) -> str | None:
    patterns = [
        r"(?:youtu\.be/|[?&]v=|/live/)([A-Za-z0-9_-]{11})",
        r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def detect_keywords(text: str) -> list[dict]:
    text_lower = text.lower()
    found = []
    seen = set()
    for kw, meta in keywords.items():
        if kw.lower() in text_lower and kw not in seen:
            seen.add(kw)
            found.append({
                "keyword": kw,
                "sector": meta.get("sector", "general"),
                "urgency": meta.get("urgency", 5),
                "text": text,
                "ts": datetime.utcnow().isoformat(),
            })
    # Sort by urgency descending
    found.sort(key=lambda x: -x["urgency"])
    return found


async def fetch_via_ytdlp(video_id: str, language: str) -> list[dict]:
    """Try yt-dlp subtitle extraction as secondary method."""
    import subprocess, json as _json, tempfile, os, sys

    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as tmp:
        out_tpl = os.path.join(tmp, "sub")
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-lang", f"{language},es,en",
            "--sub-format", "json3",
            "--output", out_tpl,
            "--quiet",
            url,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # Find any .json3 subtitle file
            for fname in os.listdir(tmp):
                if fname.endswith(".json3"):
                    with open(os.path.join(tmp, fname), encoding="utf-8") as f:
                        data = _json.load(f)
                    segs = []
                    for event in data.get("events", []):
                        segs_raw = event.get("segs", [])
                        text = "".join(s.get("utf8", "") for s in segs_raw).strip()
                        if text and text != "\n":
                            segs.append({
                                "text": text,
                                "start": event.get("tStartMs", 0) / 1000,
                                "duration": event.get("dDurationMs", 2000) / 1000,
                            })
                    log.info(f"yt-dlp got {len(segs)} segments for {video_id}")
                    return segs
        except Exception as e:
            log.warning(f"yt-dlp fallback failed for {video_id}: {e}")
    return []


async def fetch_transcript(video_id: str, language: str) -> list[dict]:
    """Fetch captions: try youtube-transcript-api first, then yt-dlp."""
    loop = asyncio.get_event_loop()

    def _ytapi_fetch():
        from youtube_transcript_api import YouTubeTranscriptApi
        langs = [language, "es", "es-419", "es-AR", "en", "a.es", "a.en"]
        for lang in langs:
            try:
                segs = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                if segs:
                    return segs
            except Exception:
                continue
        try:
            tlist = YouTubeTranscriptApi.list_transcripts(video_id)
            t = next(iter(tlist))
            return t.fetch()
        except Exception:
            return []

    # Method 1: youtube-transcript-api
    try:
        segs = await loop.run_in_executor(None, _ytapi_fetch)
        if segs:
            log.info(f"[ytapi] {len(segs)} segments for {video_id}")
            return segs
    except Exception as e:
        log.warning(f"[ytapi] failed for {video_id}: {e}")

    # Method 2: yt-dlp
    log.info(f"Trying yt-dlp fallback for {video_id}")
    segs = await fetch_via_ytdlp(video_id, language)
    if segs:
        return segs

    log.warning(f"No transcript available for {video_id}")
    return []


async def session_worker(session_id: str):
    session = sessions[session_id]
    queue: asyncio.Queue = session["queue"]
    video_id = session["video_id"]
    language = session["language"]

    log.info(f"[{session_id}] Worker started — video_id={video_id}")

    try:
        segments = await fetch_transcript(video_id, language)
    except Exception as e:
        log.error(f"[{session_id}] fetch error: {e}")
        segments = []

    if not segments:
        msg = (
            "No se encontró transcripción para este video. "
            "Verificá que el video tenga subtítulos automáticos habilitados y que sea público."
        )
        log.warning(f"[{session_id}] No transcript — {msg}")
        await queue.put({"event": "error", "data": {"message": msg}})
        session["state"] = "error"
        return

    session["state"] = "live"
    session["total_words"] = 0
    log.info(f"[{session_id}] Streaming {len(segments)} segments...")

    for seg in segments:
        if not session.get("running"):
            log.info(f"[{session_id}] Worker stopped by request")
            break

        text = seg.get("text", "").replace("\n", " ").strip()
        if not text:
            continue

        word_count = len(text.split())
        session["total_words"] = session.get("total_words", 0) + word_count

        await queue.put({
            "event": "transcript",
            "data": {
                "text": text,
                "start": round(seg.get("start", 0), 2),
                "duration": round(seg.get("duration", 0), 2),
                "session_id": session_id,
                "words": word_count,
            },
        })
        session["segments_count"] += 1

        # Keyword detection
        for alert in detect_keywords(text):
            alert["session_id"] = session_id
            await queue.put({"event": "alert", "data": alert})
            session["alerts_count"] += 1
            log.info(
                f"[{session_id}] ALERTA [{alert['urgency']}] "
                f"{alert['keyword'].upper()} | {text[:80]}"
            )

        # Heartbeat every 50 segments
        if session["segments_count"] % 50 == 0:
            await _emit_status(session_id, queue)

        await asyncio.sleep(0.12)

    # Final status
    await _emit_status(session_id, queue, state="done")
    session["state"] = "done"
    log.info(
        f"[{session_id}] Done — {session['segments_count']} segs, "
        f"{session['alerts_count']} alertas, {session.get('total_words', 0)} palabras"
    )


async def _emit_status(session_id: str, queue: asyncio.Queue, state: str | None = None):
    s = sessions[session_id]
    await queue.put({
        "event": "status",
        "data": {
            "session_id": session_id,
            "state": state or s["state"],
            "uptime_s": time.time() - s["started_at"],
            "segments_count": s["segments_count"],
            "alerts_count": s["alerts_count"],
            "total_words": s.get("total_words", 0),
        },
    })


# ── FastAPI ──────────────────────────────────────────────────────────────
app = FastAPI(title="Diaricat Live", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


class StreamStartRequest(BaseModel):
    url: str
    language: str = "es"


class KeywordAddRequest(BaseModel):
    keyword: str
    sector: str = "general"
    urgency: int = 5


@app.get("/")
def root():
    return {"status": "ok", "name": "Diaricat Live", "version": "1.0.0"}


@app.post("/v1/stream/start")
async def stream_start(req: StreamStartRequest):
    video_id = extract_video_id(req.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="URL de YouTube inválida. Usá el formato: https://www.youtube.com/watch?v=VIDEO_ID")

    session_id = f"live-{uuid.uuid4().hex[:8]}"
    queue: asyncio.Queue = asyncio.Queue(maxsize=2000)

    sessions[session_id] = {
        "session_id": session_id,
        "url": req.url,
        "video_id": video_id,
        "language": req.language,
        "state": "starting",
        "started_at": time.time(),
        "segments_count": 0,
        "alerts_count": 0,
        "total_words": 0,
        "running": True,
        "queue": queue,
    }

    asyncio.create_task(session_worker(session_id))
    log.info(f"Session creada: {session_id} — {req.url}")
    return {"session_id": session_id, "video_id": video_id, "state": "starting"}


@app.delete("/v1/stream/stop/{session_id}")
async def stream_stop(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Sesión {session_id} no encontrada")
    sessions[session_id]["running"] = False
    sessions[session_id]["state"] = "stopped"
    log.info(f"Session detenida: {session_id}")
    return {"session_id": session_id, "state": "stopped"}


@app.get("/v1/stream/status")
async def stream_status():
    now = time.time()
    return {
        "sessions": [
            {
                "session_id": sid,
                "url": s["url"],
                "state": s["state"],
                "uptime_s": round(now - s["started_at"], 1),
                "segments_count": s["segments_count"],
                "alerts_count": s["alerts_count"],
                "total_words": s.get("total_words", 0),
            }
            for sid, s in sessions.items()
        ]
    }


@app.get("/v1/stream/events/{session_id}")
async def stream_events(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Sesión {session_id} no encontrada")

    session = sessions[session_id]
    queue: asyncio.Queue = session["queue"]

    async def _generate():
        log.info(f"[{session_id}] SSE cliente conectado")
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=25.0)
                etype = event["event"]
                data = json.dumps(event["data"], ensure_ascii=False)
                yield f"event: {etype}\ndata: {data}\n\n"
                if etype == "status" and event["data"].get("state") in ("done", "error", "stopped"):
                    log.info(f"[{session_id}] SSE stream cerrado (state={event['data']['state']})")
                    break
            except asyncio.TimeoutError:
                # Heartbeat keep-alive
                s = sessions.get(session_id, {})
                hb = json.dumps({
                    "session_id": session_id,
                    "state": s.get("state", "unknown"),
                    "uptime_s": round(time.time() - s.get("started_at", time.time()), 1),
                    "segments_count": s.get("segments_count", 0),
                    "alerts_count": s.get("alerts_count", 0),
                    "total_words": s.get("total_words", 0),
                }, ensure_ascii=False)
                yield f"event: status\ndata: {hb}\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Keywords API ─────────────────────────────────────────────────────────
@app.get("/v1/keywords")
def get_keywords():
    return {kw: meta for kw, meta in sorted(keywords.items())}


@app.post("/v1/keywords")
def add_keyword(body: KeywordAddRequest):
    kw = body.keyword.lower().strip()
    if not kw:
        raise HTTPException(status_code=400, detail="Keyword vacía")
    keywords[kw] = {"sector": body.sector, "urgency": max(1, min(10, body.urgency))}
    log.info(f"Keyword añadida: '{kw}' sector={body.sector} urgency={body.urgency}")
    return {"keyword": kw, **keywords[kw]}


@app.delete("/v1/keywords/{keyword}")
def remove_keyword(keyword: str):
    kw = keyword.lower()
    if kw not in keywords:
        raise HTTPException(status_code=404, detail=f"Keyword '{kw}' no encontrada")
    del keywords[kw]
    log.info(f"Keyword eliminada: '{kw}'")
    return {"removed": kw}


if __name__ == "__main__":
    import uvicorn
    log.info(f"Iniciando Diaricat Live en http://127.0.0.1:8766")
    log.info(f"Log: {LOG_FILE}")
    uvicorn.run("diaricat_service:app", host="127.0.0.1", port=8766, reload=False)
