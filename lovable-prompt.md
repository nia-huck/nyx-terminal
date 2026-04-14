# Nyx Terminal — Lovable Build Prompt

> Pegá este prompt completo en Lovable (lovable.dev) para generar la UI.
> Después conectá el frontend generado con tu backend FastAPI en localhost:8000.

---

## PROMPT PARA LOVABLE:

Creá una aplicación web llamada **"Nyx Terminal"** — un terminal profesional de análisis económico argentino en tiempo real. Es un dashboard operativo tipo Bloomberg/Reuters pero enfocado en la economía argentina, con un mapa interactivo como pieza central.

### Stack & Configuración
- React + TypeScript + Tailwind CSS + shadcn/ui
- Recharts para gráficos
- React-Leaflet para el mapa interactivo de Argentina
- Lucide React para iconos
- Framer Motion para animaciones sutiles
- react-query (TanStack Query) para data fetching
- La app consume una REST API en `http://localhost:8000` (configurable)

### Design System — "Liquid Glass Dark"

**Paleta de colores:**
- Background: `hsl(240 10% 3.5%)` — negro profundo con tinte azul
- Surface: `hsl(240 8% 6%)` — paneles
- Surface-2: `hsl(240 8% 9%)` — cards elevados
- Foreground: `hsl(220 15% 90%)` — texto principal
- Muted: `hsl(220 8% 46%)` — texto secundario
- Border: `hsl(240 6% 12%)`
- Primary/Accent: `hsl(268 70% 58%)` — violeta (marca Nyx)
- Cyan: `hsl(192 80% 50%)` — político
- Amber: `hsl(38 92% 55%)` — regulatorio
- Red: `hsl(0 78% 58%)` — sindical
- Emerald: `hsl(152 69% 53%)` — climático

**Tipografía:**
- Display/Títulos: Space Grotesk (600-700)
- Body: Inter (400-600)
- Mono/Datos: JetBrains Mono (400-500)

**Componentes Glass:**
- Todos los paneles usan glass morphism: `backdrop-blur(16px)`, `background: hsl(240 10% 5% / 0.72)`, `border: 1px solid hsl(268 40% 40% / 0.18)`
- Border radius: 12px en paneles, 8px en cards, 6px en botones
- Sombras suaves con tinte violeta: `0 4px 30px hsl(268 50% 20% / 0.1)`

**Animaciones:**
- Entrada de paneles: fade-in + slide-up (200ms stagger entre paneles)
- Hover en cards: ligero scale(1.01) + border glow violeta
- Transiciones de datos: count-up numérico
- Skeleton loaders con shimmer animation mientras cargan datos

---

### LAYOUT PRINCIPAL (Full viewport, sin scroll)

```
┌──────────────────────────────────────────────────────────────────┐
│  [Sidebar Nav]  │              MAIN CONTENT                      │
│                 │                                                 │
│  Logo "NYX"     │   ┌─────────────────────────────────────────┐  │
│  ───────────    │   │                                         │  │
│  📊 Dashboard   │   │         MAPA INTERACTIVO               │  │
│  🗺 Mapa        │   │         DE ARGENTINA                   │  │
│  📈 Mercados    │   │         (React-Leaflet)                │  │
│  📰 Noticias    │   │                                         │  │
│  🤖 Agente IA   │   │    [Señales overlay top-right]         │  │
│                 │   │    [Event feed overlay left]            │  │
│  ───────────    │   │    [Legend overlay bottom-right]        │  │
│  ⚙ Config      │   │                                         │  │
│                 │   └─────────────────────────────────────────┘  │
│                 │   ┌─ Bottom Stats Bar ──────────────────────┐  │
│                 │   │ Dólar Blue │ Riesgo País │ Brecha │ +   │  │
│                 │   └────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

---

### COMPONENTES DETALLADOS

#### 1. Sidebar Navigation (ancho: 64px collapsed / 240px expanded)

- Logo: "N" en un cuadrado redondeado violeta (collapsed) o "NYX TERMINAL" (expanded)
- Items de navegación con iconos Lucide + label
- Secciones: Dashboard, Mapa, Mercados, Noticias, Agente IA
- Footer: Settings, estado de conexión API (dot verde/rojo)
- Tooltip en modo collapsed
- Hover: highlight sutil violeta
- Active: borde izquierdo violeta + background sutil

#### 2. Vista DASHBOARD (página principal)

Layout en grid responsive:

**Fila 1 — KPI Cards (4 columnas):**
- Dólar Blue: valor actual, variación %, sparkline 7 días
- Riesgo País: valor actual, variación, sparkline
- Inflación Mensual: último dato %, tendencia
- Reservas BCRA: valor en USD billions, tendencia

Cada card:
- Glass background
- Icono + label en muted text (font: JetBrains Mono)
- Valor grande en font-display (Space Grotesk 700)
- Variación con color (verde sube, rojo baja) y flecha ↑↓
- Mini sparkline chart (Recharts, 40px alto, sin ejes)

**Fila 2 — Charts (2 columnas 60/40):**
- Izquierda: Line chart "Evolución Dólar Blue vs Oficial" (90 días)
  - Dos líneas: blue (#8b5cf6 violeta) y oficial (#06b6d4 cyan)
  - Área rellena con gradient
  - Tooltip con fecha + valores
  - Eje Y con formato ARS $
- Derecha: Bar chart "Inflación Mensual" (12 meses)
  - Barras en gradient violeta
  - Labels con % en cada barra

**Fila 3 — Mixed (2 columnas 50/50):**
- Izquierda: "Señales de Riesgo" — 4 signal gauges:
  - Presión Cambiaria (0-100, gauge circular o barra horizontal con gradient rojo-amarillo-verde)
  - Brecha Cambiaria (%, badge de severidad)
  - Tasa Real (%, positiva=verde, negativa=rojo)
  - Tendencia Reservas (%, con icono de tendencia)
- Derecha: "Últimas Noticias" — feed scrolleable:
  - Cards con: tipo (badge color), título, fuente, hora
  - Tipos: Económico (violeta), Sindical (rojo), Regulatorio (amber), Político (cyan), Climático (emerald)
  - Max 8 items visibles, scroll suave

#### 3. Vista MAPA (fullscreen con overlays)

**Mapa base:**
- React-Leaflet con tiles CartoDB Dark Matter
- Centro: [-38.5, -63.5] (Argentina)
- Zoom: 4-5
- GeoJSON de provincias argentinas con:
  - Fill transparente, stroke sutil
  - Hover: highlight con glow violeta
  - Click: zoom-to-bounds + filtrar eventos

**Markers de eventos:**
- Clusters con conteo + color dominante
- Markers individuales: círculos con color por tipo de evento
- Tamaño proporcional a urgencia (1-10)
- Popup al click: card con título, tipo, resumen, urgencia badge, source link

**Overlay panels (sobre el mapa):**

a) **Panel Señales** (top-right, ~280px ancho):
  - 4 signal cards compactos
  - Glass background
  - Collapsible

b) **Panel Event Feed** (left, ~320px ancho):
  - Header: "Eventos" + count badge
  - Lista de provincias con conteo de eventos
  - Click provincia → filtra eventos + lista detallada
  - Botón back para volver a vista general
  - Collapsible con botón toggle

c) **Leyenda** (bottom-right):
  - Grid 2x3 con tipos de evento + color
  - Glass background, compacta

d) **Stats Bar** (bottom center):
  - Horizontal, glass, ~500px ancho
  - 4 stats: Dólar Blue, Riesgo País, Brecha %, Total Eventos
  - Dividers verticales entre stats
  - Valores en JetBrains Mono, labels en Inter muted

#### 4. Vista MERCADOS

**Tabla de Cotizaciones:**
- Tabla con todas las cotizaciones del dólar:
  - Blue, Oficial, MEP, CCL, Mayorista, Cripto, Tarjeta
  - Columnas: Tipo, Compra, Venta, Variación %, Última actualización
  - Rows con hover highlight
  - Variación con color semántico

**Charts de mercado:**
- Dólar histórico (seleccionable: Blue, MEP, CCL, etc.)
- Riesgo País histórico (90 días)
- Reservas BCRA (30 días)
- Cada chart: selectable timeframe (7d, 30d, 90d)

**Variables BCRA:**
- Grid de cards con:
  - BADLAR, TM20, Base Monetaria
  - Valor actual + variación

#### 5. Vista NOTICIAS

**Layout masonry o grid 3 columnas:**
- Cards de noticias con:
  - Badge de tipo (color coded)
  - Título (truncado 2 líneas)
  - Fuente + fecha
  - Resumen (truncado 3 líneas)
  - Tags de activos afectados (badges)
  - Urgencia: badge (Crítico=rojo, Alto=amber, Moderado=cyan, Bajo=gray)
- Filtros top:
  - Por tipo (chips seleccionables con color)
  - Por fuente (Ámbito, Cronista, Infobae, etc.)
  - Por urgencia
  - Search bar
- Paginación o infinite scroll

#### 6. Vista AGENTE IA (Chat)

**Layout split: 60% chat / 40% context panel**

Chat (izquierda):
- Header: "NYX · AGENTE ECONÓMICO" con dot pulsante violeta
- Messages area scrolleable:
  - User messages: alineados derecha, bg surface-2
  - Nyx messages: alineados izquierda, bg glass con borde violeta sutil
  - Metadata row después de cada respuesta Nyx: "3 tools · 2.1s · $0.02 Apify"
- Quick action buttons (chips):
  - "Dólar hoy"
  - "Riesgo semanal"
  - "Twitter inflación"
  - "Conflictos sindicales"
- Input bar bottom:
  - Glass input con placeholder "Preguntá sobre dólar, inflación, BCRA..."
  - Send button violeta
  - Typing indicator: 3 dots animados

Context panel (derecha):
- Muestra datos relevantes al último mensaje
- Si el agente usó herramientas, muestra cards con:
  - Herramienta usada
  - Datos consultados
  - Mini visualizaciones inline

---

### API ENDPOINTS (para conectar)

La app debe consumir estos endpoints desde `http://localhost:8000`:

```
GET  /                    → Health check
GET  /summary             → Resumen general
GET  /dolar               → Todas las cotizaciones
GET  /dolar/blue          → Dólar blue actual
GET  /dolar/historial/{tipo}?dias=30  → Historial
GET  /bcra/{variable}     → Variables BCRA
GET  /reservas            → Reservas internacionales
GET  /riesgo-pais         → Riesgo país actual
GET  /riesgo-pais/historial?dias=30  → Historial
GET  /inflacion?meses=12  → Inflación mensual
GET  /signals             → Todas las señales
GET  /signals/brecha      → Brecha cambiaria
GET  /signals/tasa-real   → Tasa real
GET  /signals/reservas    → Tendencia reservas
GET  /signals/presion     → Presión cambiaria
GET  /noticias            → Noticias clasificadas
GET  /eventos             → Eventos geolocalizados
GET  /tweets              → Tweets económicos
GET  /reddit              → Posts Reddit
GET  /trends              → Google Trends
POST /agent/ask           → { question, max_budget } → Respuesta del agente IA
```

Usá React Query para el fetching con:
- staleTime: 60 segundos para datos financieros
- refetchInterval: 120 segundos para datos que se actualizan
- Skeleton loaders mientras carga
- Error states con mensaje y retry button

---

### UX/UI BEST PRACTICES

1. **Información jerárquica**: Lo más importante (KPIs) siempre visible, detalles on-demand
2. **Feedback visual**: Loading states, hover states, active states en todo componente interactivo
3. **Consistencia cromática**: Cada tipo de evento SIEMPRE usa el mismo color en toda la app
4. **Responsive**: Funciona en desktop (1280px+) y tablets. Mobile no es prioridad pero debe ser usable
5. **Accesibilidad**: Contraste AA en textos sobre glass, focus visible en navegación por teclado
6. **Performance**: Lazy loading de vistas, memoización de componentes pesados (mapa, charts)
7. **Empty states**: Mensajes claros cuando no hay datos ("Sin eventos en esta provincia")
8. **Error handling**: Toast notifications para errores de API, retry automático
9. **Microinteracciones**: Números que hacen count-up al cargar, badges que pulsan en alertas críticas
10. **Data density**: Inspirado en terminales financieras — mucha info, poco desperdicio de espacio

### Detalles finales
- El título de la app en el tab del browser debe ser "Nyx Terminal"
- Favicon: cuadrado violeta con "N" blanco
- No usar emojis en la UI, usar iconos Lucide
- Todos los textos en español argentino
- Formatos: números con separador de miles (.) y decimales (,) — formato argentino
- Moneda: ARS $ para pesos, USD para dólares
- Fechas: formato dd/mm/yyyy HH:mm
