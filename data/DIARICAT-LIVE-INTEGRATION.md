# Integración Nyx Terminal ↔ Diaricat Live

## Contexto

Diaricat Live es un servicio headless (FastAPI, puerto 8766) que captura audio de streams de YouTube/internet, lo transcribe en tiempo real con Faster Whisper, y emite eventos (transcripciones + alertas financieras) via SSE.

Nyx Terminal necesita consumir esos eventos para mostrar:
- Una ventana pequeña abajo con el video de YouTube embebido
- Transcripción en vivo al lado del video
- Alertas destacadas cuando se detectan keywords financieros

---

## Arquitectura

```
┌─────────────────────────────────────────────┐
│           NYX TERMINAL (frontend)           │
│                                             │
│  Panel principal: dashboard, dólar, eventos │
│                                             │
├──────────────────────┬──────────────────────┤
│  YouTube embed       │  Transcripción live  │
│  <iframe>            │  + Alertas           │
│  [input URL] [▶] [■] │                     │
└──────────────────────┴──────────────────────┘
        │                       ▲
        │ POST /start           │ SSE /events
        ▼                       │
┌─────────────────────────────────────────────┐
│         DIARICAT LIVE (puerto 8766)         │
│  yt-dlp → ffmpeg → Whisper → AlertService   │
└─────────────────────────────────────────────┘
```

---

## API de Diaricat Live

Base URL: `http://127.0.0.1:8766`

### Iniciar transcripción

```
POST /v1/stream/start
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=cb12KmMMDJA",
  "language": "es",
  "keywords": ["Milei", "importaciones"]  // opcional, extras
}

→ { "session_id": "live-0001", "state": "starting" }
```

### Escuchar eventos (SSE)

```
GET /v1/stream/events/live-0001     ← una sesión
GET /v1/stream/events               ← todas las sesiones mezcladas
```

Eventos que emite:

```
event: transcript
data: {"type":"transcript","session_id":"live-0001","text":"El ministro dijo que...","start":125.3,"end":130.1,"language":"es","ts":"..."}

event: alert
data: {"type":"alert","session_id":"live-0001","keyword":"dólar","text":"...mencionó el dólar blue...","urgency":7,"sector":"finanzas","ts":"..."}

event: status
data: {"type":"status","session_id":"live-0001","state":"listening","uptime_s":3600,"segments_count":720,"alerts_count":5,"ts":"..."}

event: error
data: {"type":"error","session_id":"live-0001","message":"Stream ended","ts":"..."}
```

### Parar transcripción

```
POST /v1/stream/stop
Content-Type: application/json

{ "session_id": "live-0001" }

→ { "status": "stopped", "session_id": "live-0001" }
```

### Ver sesiones activas

```
GET /v1/stream/status

→ {
    "sessions": [
      {
        "session_id": "live-0001",
        "url": "https://...",
        "state": "listening",
        "uptime_s": 120.5,
        "segments_count": 24,
        "alerts_count": 2
      }
    ]
  }
```

### Health check

```
GET /health → { "status": "ok", "service": "diaricat-live" }
```

---

## Conexión desde el frontend (React/JS)

### 1. Iniciar stream

```js
async function startStream(youtubeUrl) {
  const res = await fetch("http://127.0.0.1:8766/v1/stream/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: youtubeUrl, language: "es" }),
  });
  const { session_id } = await res.json();
  return session_id;
}
```

### 2. Escuchar eventos SSE

```js
function listenToStream(sessionId, onTranscript, onAlert) {
  const es = new EventSource(
    `http://127.0.0.1:8766/v1/stream/events/${sessionId}`
  );

  es.addEventListener("transcript", (e) => {
    const data = JSON.parse(e.data);
    onTranscript(data);
    // data.text = "El ministro dijo que..."
    // data.start, data.end = timestamps en segundos
  });

  es.addEventListener("alert", (e) => {
    const data = JSON.parse(e.data);
    onAlert(data);
    // data.keyword = "dólar"
    // data.text = contexto donde apareció
    // data.urgency = 7 (1-10)
    // data.sector = "finanzas"
  });

  es.addEventListener("status", (e) => {
    const data = JSON.parse(e.data);
    // data.segments_count, data.alerts_count, data.uptime_s
  });

  es.addEventListener("error", (e) => {
    const data = JSON.parse(e.data);
    console.error("Stream error:", data.message);
  });

  return es; // guardar referencia para cerrar: es.close()
}
```

### 3. Parar stream

```js
async function stopStream(sessionId) {
  await fetch("http://127.0.0.1:8766/v1/stream/stop", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
}
```

### 4. Embed de YouTube

La misma URL que le pasás a la API se puede embeber como iframe:

```jsx
function YouTubeEmbed({ url }) {
  // Extraer video ID de la URL
  const videoId = new URL(url).searchParams.get("v");
  return (
    <iframe
      width="100%"
      height="100%"
      src={`https://www.youtube.com/embed/${videoId}?autoplay=1&mute=1`}
      allow="autoplay"
      frameBorder="0"
    />
  );
}
```

Nota: el iframe va muteado porque Diaricat Live captura el audio directo del stream (no necesita el audio del browser).

---

## Componente completo de ejemplo

```jsx
function DiaricatLivePanel() {
  const [sessionId, setSessionId] = useState(null);
  const [url, setUrl] = useState("");
  const [transcripts, setTranscripts] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const esRef = useRef(null);

  const handleStart = async () => {
    const sid = await startStream(url);
    setSessionId(sid);

    esRef.current = listenToStream(
      sid,
      (t) => setTranscripts((prev) => [...prev.slice(-50), t]),
      (a) => setAlerts((prev) => [a, ...prev].slice(0, 20))
    );
  };

  const handleStop = async () => {
    if (esRef.current) esRef.current.close();
    if (sessionId) await stopStream(sessionId);
    setSessionId(null);
  };

  const videoId = url && new URL(url).searchParams.get("v");

  return (
    <div className="diaricat-panel">
      {/* Controles */}
      <div className="controls">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="YouTube URL..."
        />
        {!sessionId ? (
          <button onClick={handleStart}>▶ Iniciar</button>
        ) : (
          <button onClick={handleStop}>■ Detener</button>
        )}
      </div>

      <div className="content">
        {/* YouTube embed */}
        {videoId && (
          <div className="video">
            <iframe
              src={`https://www.youtube.com/embed/${videoId}?autoplay=1&mute=1`}
              allow="autoplay"
            />
          </div>
        )}

        {/* Transcripción */}
        <div className="transcript">
          {alerts.map((a, i) => (
            <div key={`a-${i}`} className="alert" data-urgency={a.urgency}>
              ⚠ [{a.sector}] {a.keyword}: {a.text}
            </div>
          ))}
          {transcripts.map((t, i) => (
            <div key={`t-${i}`} className="segment">
              {t.text}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## Keywords de alerta incluidos por defecto

Diaricat Live detecta automáticamente estos términos:

| Keyword | Sector | Urgencia |
|---|---|---|
| dólar, blue, CCL, MEP | finanzas | 6-7 |
| cepo, devaluación | finanzas | 9 |
| BCRA, banco central, tasa de interés | finanzas | 7-8 |
| inflación, IPC, recesión, PBI | economia | 7-8 |
| FMI, desembolso | economia | 8-9 |
| merval, bonos, riesgo país | mercado | 6-7 |
| paritarias, paro, huelga, CGT | sindical | 6-8 |
| YPF, Vaca Muerta, tarifas | energia | 6-7 |
| soja | agro | 6 |

Se pueden agregar más en el request de start (`"keywords": [...]`) o via archivo `keywords.yaml`.

---

## Formato de alertas compatible con nyx-events

Las alertas se pueden convertir al formato de `nyx-events-demo.json`:

```js
function alertToNyxEvent(alert) {
  return {
    id: Date.now(),
    titulo: `[LIVE] ${alert.keyword.toUpperCase()}: ${alert.text.slice(0, 80)}`,
    tipo: alert.sector === "sindical" ? "sindical" : "economico",
    sector: [alert.sector],
    urgencia: alert.urgency,
    fecha: new Date().toISOString().split("T")[0],
    resumen: alert.text,
    fuente: "Diaricat Live",
    fuente_url: "",
    activos_afectados: [],
    horizonte_impacto: "inmediato",
  };
}
```

---

## Levantar el servicio

```bash
cd "C:\Users\Niahu\OneDrive\Desktop\diaricat-live"
python -m diaricat_live.run
# → Uvicorn running on http://127.0.0.1:8766
```

Requiere: Python 3.11+, ffmpeg (usa el de Diaricat), yt-dlp, faster-whisper.
Ya está todo instalado. Solo correr el comando.

---

## Notas para el hackathon

- El modelo Whisper large-v3 tarda ~15s en cargar la primera vez, después queda en memoria
- Corre en CPU (int8) porque falta cuBLAS para CUDA en esta máquina
- Soporta hasta 3 streams simultáneos (configurable en .env)
- Cada chunk de audio es ~5 segundos, la transcripción llega ~8-10s después en CPU
- El SSE tiene heartbeat cada 30s para mantener la conexión viva
- Si el stream de YouTube se corta, la sesión pasa a estado "stopped"
- CORS está habilitado para localhost — si el frontend corre en otro puerto, funciona
