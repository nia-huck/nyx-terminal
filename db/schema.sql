-- Nyx Terminal — PostgreSQL Schema
-- Base de datos para contexto economico argentino con indexacion full-text
-- Diseñada para: lectura rapida por agente IA + escritura incremental via scraping

-- ═══════════════════════════════════════════════════════
--  EXTENSIONES
-- ═══════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- Fuzzy text search
CREATE EXTENSION IF NOT EXISTS unaccent;      -- sin acentos para busquedas

-- Configurar busqueda en español
DO $$ BEGIN
    PERFORM ts_debug('spanish', 'test');
EXCEPTION WHEN undefined_object THEN
    -- spanish config no disponible, usar default
    NULL;
END $$;

-- ═══════════════════════════════════════════════════════
--  COTIZACIONES — Dolar, tasas, indices
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS cotizaciones (
    id          BIGSERIAL PRIMARY KEY,
    tipo        TEXT NOT NULL,           -- 'dolar_blue', 'dolar_oficial', 'dolar_mep', 'riesgo_pais', etc.
    fecha       DATE NOT NULL,
    compra      NUMERIC(12,2),
    venta       NUMERIC(12,2),
    valor       NUMERIC(16,4),           -- Para datos que no son compra/venta (riesgo_pais, tasas, IPC)
    fuente      TEXT DEFAULT 'seed',     -- 'seed', 'apify', 'bcra_api', 'agent'
    meta        JSONB,                   -- Metadata extra flexible
    created_at  TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tipo, fecha)
);

CREATE INDEX IF NOT EXISTS idx_cotiz_tipo_fecha ON cotizaciones(tipo, fecha DESC);
CREATE INDEX IF NOT EXISTS idx_cotiz_fecha ON cotizaciones(fecha DESC);

-- ═══════════════════════════════════════════════════════
--  BCRA — Variables monetarias y cambiarias
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS bcra_variables (
    id          BIGSERIAL PRIMARY KEY,
    variable    TEXT NOT NULL,            -- 'reservas_internacionales', 'base_monetaria', etc.
    fecha       DATE NOT NULL,
    valor       NUMERIC(20,4) NOT NULL,
    fuente      TEXT DEFAULT 'seed',
    created_at  TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(variable, fecha)
);

CREATE INDEX IF NOT EXISTS idx_bcra_var_fecha ON bcra_variables(variable, fecha DESC);

-- ═══════════════════════════════════════════════════════
--  NOTICIAS — RSS, articulos, RAG
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS noticias (
    id          BIGSERIAL PRIMARY KEY,
    titulo      TEXT NOT NULL,
    resumen     TEXT,
    texto       TEXT,                     -- Texto completo (articles, RAG)
    url         TEXT,
    fuente      TEXT NOT NULL,            -- 'rss_ambito', 'article_infobae', 'rag_bcra', 'apify', 'agent'
    categoria   TEXT,                     -- 'economia', 'finanzas', 'politica', etc.
    fecha       TIMESTAMPTZ,
    autor       TEXT,
    meta        JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW(),

    -- Full-text search vector
    tsv         TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('spanish', coalesce(titulo, '')), 'A') ||
        setweight(to_tsvector('spanish', coalesce(resumen, '')), 'B') ||
        setweight(to_tsvector('spanish', coalesce(texto, '')), 'C')
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_noticias_tsv ON noticias USING GIN(tsv);
CREATE INDEX IF NOT EXISTS idx_noticias_fuente ON noticias(fuente);
CREATE INDEX IF NOT EXISTS idx_noticias_fecha ON noticias(fecha DESC);
CREATE INDEX IF NOT EXISTS idx_noticias_categoria ON noticias(categoria);

-- Unique constraint para evitar duplicados (solo URLs reales, no vacias)
CREATE UNIQUE INDEX IF NOT EXISTS idx_noticias_url ON noticias(url) WHERE url IS NOT NULL AND url != '';

-- ═══════════════════════════════════════════════════════
--  SOCIAL — Tweets, Reddit
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS tweets (
    id              BIGSERIAL PRIMARY KEY,
    tweet_id        TEXT UNIQUE,
    texto           TEXT NOT NULL,
    autor           TEXT,
    likes           INTEGER DEFAULT 0,
    retweets        INTEGER DEFAULT 0,
    replies         INTEGER DEFAULT 0,
    query_origen    TEXT,                  -- 'dolar_blue', 'inflacion', etc.
    fecha           TIMESTAMPTZ,
    url             TEXT,
    fuente          TEXT DEFAULT 'seed',   -- 'seed', 'apify'
    meta            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    tsv             TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('spanish', coalesce(texto, ''))
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_tweets_tsv ON tweets USING GIN(tsv);
CREATE INDEX IF NOT EXISTS idx_tweets_query ON tweets(query_origen);
CREATE INDEX IF NOT EXISTS idx_tweets_fecha ON tweets(fecha DESC);

CREATE TABLE IF NOT EXISTS reddit_posts (
    id              BIGSERIAL PRIMARY KEY,
    post_id         TEXT UNIQUE,
    titulo          TEXT NOT NULL,
    cuerpo          TEXT,
    autor           TEXT,
    score           INTEGER DEFAULT 0,
    comentarios     INTEGER DEFAULT 0,
    subreddit       TEXT,
    url             TEXT,
    fecha           TIMESTAMPTZ,
    fuente          TEXT DEFAULT 'seed',
    meta            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    tsv             TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('spanish', coalesce(titulo, '')), 'A') ||
        setweight(to_tsvector('spanish', coalesce(cuerpo, '')), 'B')
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_reddit_tsv ON reddit_posts USING GIN(tsv);
CREATE INDEX IF NOT EXISTS idx_reddit_sub ON reddit_posts(subreddit);
CREATE INDEX IF NOT EXISTS idx_reddit_fecha ON reddit_posts(fecha DESC);

-- ═══════════════════════════════════════════════════════
--  EVENTOS — Clasificados por el classifier + agente
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS eventos (
    id              BIGSERIAL PRIMARY KEY,
    titulo          TEXT NOT NULL,
    tipo            TEXT NOT NULL,          -- 'sindical', 'regulatorio', 'economico', 'politico', 'climatico'
    urgencia        INTEGER DEFAULT 5,      -- 1-10
    sector          TEXT[],
    activos_afectados TEXT[],
    provincia       TEXT,
    lat             NUMERIC(9,6),
    lon             NUMERIC(9,6),
    fecha           TIMESTAMPTZ,
    resumen         TEXT,
    fuente          TEXT,
    fuente_url      TEXT,
    horizonte       TEXT,                   -- '24h', '1 semana', etc.
    noticia_id      BIGINT REFERENCES noticias(id),
    fuente_tipo     TEXT DEFAULT 'classifier', -- 'classifier', 'agent', 'manual'
    meta            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    tsv             TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('spanish', coalesce(titulo, '')), 'A') ||
        setweight(to_tsvector('spanish', coalesce(resumen, '')), 'B')
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_eventos_tsv ON eventos USING GIN(tsv);
CREATE INDEX IF NOT EXISTS idx_eventos_tipo ON eventos(tipo);
CREATE INDEX IF NOT EXISTS idx_eventos_urgencia ON eventos(urgencia DESC);
CREATE INDEX IF NOT EXISTS idx_eventos_fecha ON eventos(fecha DESC);

-- ═══════════════════════════════════════════════════════
--  CONTEXTO AGENTE — Lo que el agente escribe/aprende
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS agente_contexto (
    id              BIGSERIAL PRIMARY KEY,
    tipo            TEXT NOT NULL,          -- 'insight', 'alerta', 'tendencia', 'dato', 'resumen_diario'
    titulo          TEXT NOT NULL,
    contenido       TEXT NOT NULL,
    relevancia      NUMERIC(3,1) DEFAULT 5, -- 0-10, decae con el tiempo
    tags            TEXT[],
    fuentes         TEXT[],                 -- URLs o refs que usó el agente
    vigente_hasta   DATE,                   -- Fecha de expiracion del insight
    meta            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    tsv             TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('spanish', coalesce(titulo, '')), 'A') ||
        setweight(to_tsvector('spanish', coalesce(contenido, '')), 'B')
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_ctx_tsv ON agente_contexto USING GIN(tsv);
CREATE INDEX IF NOT EXISTS idx_ctx_tipo ON agente_contexto(tipo);
CREATE INDEX IF NOT EXISTS idx_ctx_tags ON agente_contexto USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_ctx_relevancia ON agente_contexto(relevancia DESC);
CREATE INDEX IF NOT EXISTS idx_ctx_vigente ON agente_contexto(vigente_hasta);

-- ═══════════════════════════════════════════════════════
--  SNAPSHOTS — Estado calculado periodico
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS snapshots (
    id              BIGSERIAL PRIMARY KEY,
    tipo            TEXT NOT NULL,          -- 'indice_nyx', 'resumen_ejecutivo', 'reporte_completo'
    fecha           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    datos           JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_snap_tipo_fecha ON snapshots(tipo, fecha DESC);

-- ═══════════════════════════════════════════════════════
--  TRENDS — Google Trends
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS trends (
    id              BIGSERIAL PRIMARY KEY,
    termino         TEXT NOT NULL,
    fecha           DATE NOT NULL,
    valor           INTEGER,               -- 0-100 relative interest
    fuente          TEXT DEFAULT 'seed',
    meta            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(termino, fecha)
);

CREATE INDEX IF NOT EXISTS idx_trends_term ON trends(termino, fecha DESC);

-- ═══════════════════════════════════════════════════════
--  RENDIMIENTOS — Plazo fijo + crypto
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS rendimientos (
    id              BIGSERIAL PRIMARY KEY,
    tipo            TEXT NOT NULL,          -- 'plazo_fijo', 'crypto'
    entidad         TEXT NOT NULL,
    moneda          TEXT,                   -- 'ARS', 'USDT', 'BTC', etc.
    tasa            NUMERIC(8,4),           -- TNA para PF, APY para crypto
    fecha           DATE NOT NULL,
    fuente          TEXT DEFAULT 'seed',
    meta            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tipo, entidad, moneda, fecha)
);

CREATE INDEX IF NOT EXISTS idx_rend_tipo ON rendimientos(tipo, fecha DESC);

-- ═══════════════════════════════════════════════════════
--  FUNCIONES UTILITARIAS
-- ═══════════════════════════════════════════════════════

-- Busqueda full-text unificada en todas las tablas con datos de citacion
CREATE OR REPLACE FUNCTION buscar_contexto(query_text TEXT, limite INTEGER DEFAULT 20)
RETURNS TABLE(
    tabla TEXT,
    id BIGINT,
    titulo TEXT,
    resumen TEXT,
    url TEXT,
    fuente TEXT,
    fecha TIMESTAMPTZ,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    WITH resultados AS (
        SELECT 'noticias'::TEXT as tabla, n.id, n.titulo, n.resumen,
               n.url, n.fuente,
               n.fecha, ts_rank(n.tsv, websearch_to_tsquery('spanish', query_text)) as rank
        FROM noticias n
        WHERE n.tsv @@ websearch_to_tsquery('spanish', query_text)

        UNION ALL

        SELECT 'tweets'::TEXT, t.id,
               LEFT(t.texto, 120) as titulo, t.texto as resumen,
               t.url, COALESCE('twitter/' || t.query_origen, 'twitter') as fuente,
               t.fecha, ts_rank(t.tsv, websearch_to_tsquery('spanish', query_text))
        FROM tweets t
        WHERE t.tsv @@ websearch_to_tsquery('spanish', query_text)

        UNION ALL

        SELECT 'reddit'::TEXT, r.id, r.titulo, LEFT(r.cuerpo, 500),
               r.url, COALESCE('reddit/' || r.subreddit, 'reddit') as fuente,
               r.fecha, ts_rank(r.tsv, websearch_to_tsquery('spanish', query_text))
        FROM reddit_posts r
        WHERE r.tsv @@ websearch_to_tsquery('spanish', query_text)

        UNION ALL

        SELECT 'eventos'::TEXT, e.id, e.titulo, e.resumen,
               e.fuente_url as url, e.fuente,
               e.fecha, ts_rank(e.tsv, websearch_to_tsquery('spanish', query_text))
        FROM eventos e
        WHERE e.tsv @@ websearch_to_tsquery('spanish', query_text)

        UNION ALL

        SELECT 'contexto'::TEXT, c.id, c.titulo, LEFT(c.contenido, 500),
               NULL::TEXT as url, c.tipo as fuente,
               c.created_at, ts_rank(c.tsv, websearch_to_tsquery('spanish', query_text))
        FROM agente_contexto c
        WHERE c.tsv @@ websearch_to_tsquery('spanish', query_text)
    )
    SELECT * FROM resultados
    ORDER BY rank DESC
    LIMIT limite;
END;
$$ LANGUAGE plpgsql;
