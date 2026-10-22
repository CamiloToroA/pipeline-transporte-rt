-- Esquema de ingesta en tiempo real (idempotente: se aplica al iniciar el scheduler)

-- 1. Bitácora de ciclos: una fila por cada consulta a la API (por línea).
--    Permite medir la completitud de la serie histórica y auditar fallos.
CREATE TABLE IF NOT EXISTS ciclos_rt (
    ciclo_id              BIGSERIAL PRIMARY KEY,
    linea_id              TEXT        NOT NULL,
    inicio                TIMESTAMPTZ NOT NULL,
    fin                   TIMESTAMPTZ,
    -- OK | VACIO | ERROR_RED | ERROR_HTTP | ERROR_API | ERROR_FORMATO | ERROR_DB
    estado                TEXT        NOT NULL,
    http_status           INTEGER,
    fecha_peticion        TIMESTAMPTZ,
    desfase_seg           NUMERIC,    -- fecha_peticion - inicio (detecta respuestas cacheadas)
    registros_validos     INTEGER     NOT NULL DEFAULT 0,
    registros_insertados  INTEGER     NOT NULL DEFAULT 0,
    registros_rechazados  INTEGER     NOT NULL DEFAULT 0,
    detalle               TEXT
);

CREATE INDEX IF NOT EXISTS idx_ciclos_rt_inicio ON ciclos_rt (inicio);

-- 2. Observaciones válidas: un bus reportado en una parada en un instante.
CREATE TABLE IF NOT EXISTS bus_parada_rt (
    id              BIGSERIAL PRIMARY KEY,
    ciclo_id        BIGINT      REFERENCES ciclos_rt (ciclo_id),
    linea_id        TEXT        NOT NULL,
    sentido         TEXT        NOT NULL,
    parada_id       TEXT        NOT NULL,
    bus_id          TEXT        NOT NULL,
    estado          TEXT,
    distancia       NUMERIC     CHECK (distancia >= 0),
    fecha_peticion  TIMESTAMPTZ NOT NULL,
    extraido_en     TIMESTAMPTZ NOT NULL,
    -- Evita duplicados si la API repite la misma instantánea
    CONSTRAINT uq_bus_parada_rt UNIQUE (linea_id, fecha_peticion, sentido, parada_id, bus_id)
);

CREATE INDEX IF NOT EXISTS idx_bus_parada_rt_fecha ON bus_parada_rt (fecha_peticion);

-- 3. Dimensiones para análisis/BI, cargadas desde el GTFS estático al iniciar.
--    Los parada_id de la API coinciden con stop_id del GTFS.
CREATE TABLE IF NOT EXISTS dim_linea (
    linea_id      TEXT PRIMARY KEY,   -- route_id
    nombre_corto  TEXT,
    nombre        TEXT,
    tipologia     TEXT,
    monitoreada   BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS dim_parada (
    parada_id  TEXT PRIMARY KEY,      -- stop_id
    nombre     TEXT,
    latitud    NUMERIC,
    longitud   NUMERIC
);

-- 4. Registros rechazados por validación, con el motivo y el dato original.
CREATE TABLE IF NOT EXISTS rechazos_rt (
    id           BIGSERIAL PRIMARY KEY,
    ciclo_id     BIGINT      REFERENCES ciclos_rt (ciclo_id),
    linea_id     TEXT        NOT NULL,
    motivo       TEXT        NOT NULL,
    payload      JSONB,
    extraido_en  TIMESTAMPTZ NOT NULL
);
