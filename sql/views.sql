-- Vistas analíticas para el pipeline de transporte en tiempo real
-- Las horas se expresan en hora local de A Coruña (Europe/Madrid).
-- Cada vista se elimina y se recrea: CREATE OR REPLACE no permite cambiar tipos de columna
-- (las vistas antiguas tenían parada_id como bigint).

-- 1. Flota activa por hora (todas las líneas monitoreadas)
DROP VIEW IF EXISTS v_flota_activa_hora;
CREATE VIEW v_flota_activa_hora AS
SELECT
    DATE_TRUNC('hour', fecha_peticion AT TIME ZONE 'Europe/Madrid') AS hora_registro,
    COUNT(DISTINCT bus_id) AS total_buses_activos,
    COUNT(DISTINCT parada_id) AS paradas_con_actividad,
    COUNT(*) AS total_registros
FROM
    bus_parada_rt
GROUP BY
    1
ORDER BY
    hora_registro DESC;


-- 2. Paradas con mayor movimiento o afluencia de buses
DROP VIEW IF EXISTS v_top_paradas_frecuentes;
CREATE VIEW v_top_paradas_frecuentes AS
SELECT
    parada_id,
    sentido,
    COUNT(DISTINCT bus_id) AS total_buses_unicos,
    COUNT(*) AS total_interacciones,
    MAX(fecha_peticion AT TIME ZONE 'Europe/Madrid') AS ultimo_reporte
FROM
    bus_parada_rt
GROUP BY
    parada_id,
    sentido
ORDER BY
    total_interacciones DESC;


-- 3. Resumen diario para validar que el pipeline y el scheduler corren bien
DROP VIEW IF EXISTS v_salud_pipeline_diario;
CREATE VIEW v_salud_pipeline_diario AS
SELECT
    DATE(fecha_peticion AT TIME ZONE 'Europe/Madrid') AS fecha,
    COUNT(*) AS total_registros,
    COUNT(DISTINCT bus_id) AS total_buses,
    MIN(fecha_peticion AT TIME ZONE 'Europe/Madrid') AS inicio_captura,
    MAX(fecha_peticion AT TIME ZONE 'Europe/Madrid') AS fin_captura
FROM
    bus_parada_rt
GROUP BY
    1
ORDER BY
    fecha DESC;


-- 4. Flota activa por hora y por línea (comparación entre tipologías)
DROP VIEW IF EXISTS v_flota_activa_hora_linea;
CREATE VIEW v_flota_activa_hora_linea AS
SELECT
    linea_id,
    DATE_TRUNC('hour', fecha_peticion AT TIME ZONE 'Europe/Madrid') AS hora_registro,
    COUNT(DISTINCT bus_id) AS total_buses_activos,
    COUNT(DISTINCT parada_id) AS paradas_con_actividad,
    COUNT(*) AS total_registros
FROM
    bus_parada_rt
GROUP BY
    1, 2
ORDER BY
    hora_registro DESC, linea_id;


-- 5. Completitud de la captura: ciclos exitosos vs. fallidos por día y línea
DROP VIEW IF EXISTS v_completitud_diaria;
CREATE VIEW v_completitud_diaria AS
SELECT
    DATE(inicio AT TIME ZONE 'Europe/Madrid') AS fecha,
    linea_id,
    COUNT(*) AS ciclos_totales,
    COUNT(*) FILTER (WHERE estado = 'OK') AS ciclos_ok,
    COUNT(*) FILTER (WHERE estado = 'VACIO') AS ciclos_vacios,
    COUNT(*) FILTER (WHERE estado LIKE 'ERROR%') AS ciclos_error,
    ROUND(100.0 * COUNT(*) FILTER (WHERE estado = 'OK') / COUNT(*), 2) AS pct_ok,
    SUM(registros_insertados) AS registros_insertados,
    SUM(registros_validos - registros_insertados) AS registros_duplicados,
    SUM(registros_rechazados) AS registros_rechazados,
    ROUND(AVG(desfase_seg), 1) AS desfase_promedio_seg
FROM
    ciclos_rt
GROUP BY
    1, 2
ORDER BY
    fecha DESC, linea_id;


-- 6. Motivos de rechazo de la validación
DROP VIEW IF EXISTS v_rechazos_motivo;
CREATE VIEW v_rechazos_motivo AS
SELECT
    DATE(extraido_en AT TIME ZONE 'Europe/Madrid') AS fecha,
    linea_id,
    motivo,
    COUNT(*) AS total
FROM
    rechazos_rt
GROUP BY
    1, 2, 3
ORDER BY
    fecha DESC, total DESC;


-- ===================================================================
-- Vistas para Power BI (modelo estrella). Toda fecha/hora ya viene en
-- hora local de A Coruña, así Power BI no hace conversiones de zona.
-- ===================================================================

-- Hechos: un bus observado en una parada en una captura
DROP VIEW IF EXISTS bi_observaciones;
CREATE VIEW bi_observaciones AS
SELECT
    o.id,
    o.ciclo_id,
    o.linea_id,
    o.sentido,
    CASE o.sentido WHEN '0' THEN 'Ida' WHEN '1' THEN 'Vuelta' ELSE 'Otro' END AS sentido_etiqueta,
    o.parada_id,
    o.bus_id,
    o.estado,
    CASE o.estado
        WHEN '0'  THEN 'En parada'
        WHEN '1'  THEN 'En movimiento'
        WHEN '16' THEN 'Extensión / cocheras'
        WHEN '17' THEN 'Incorporando a ruta'
        ELSE 'Otro'
    END AS estado_etiqueta,
    o.distancia,
    o.fecha_peticion AT TIME ZONE 'Europe/Madrid' AS fecha_hora,
    DATE_TRUNC('minute', o.fecha_peticion AT TIME ZONE 'Europe/Madrid') AS minuto,
    (o.fecha_peticion AT TIME ZONE 'Europe/Madrid')::DATE AS fecha,
    EXTRACT(HOUR FROM o.fecha_peticion AT TIME ZONE 'Europe/Madrid')::INTEGER AS hora
FROM bus_parada_rt o;


-- Hechos: cada consulta a la API (base para completitud y disponibilidad)
DROP VIEW IF EXISTS bi_ciclos;
CREATE VIEW bi_ciclos AS
SELECT
    c.ciclo_id,
    c.linea_id,
    c.estado,
    CASE
        WHEN c.estado = 'OK' THEN 'Con datos'
        WHEN c.estado = 'VACIO' THEN 'Sin buses'
        ELSE 'Error'
    END AS estado_grupo,
    c.http_status,
    c.inicio AT TIME ZONE 'Europe/Madrid' AS fecha_hora,
    (c.inicio AT TIME ZONE 'Europe/Madrid')::DATE AS fecha,
    EXTRACT(HOUR FROM c.inicio AT TIME ZONE 'Europe/Madrid')::INTEGER AS hora,
    EXTRACT(EPOCH FROM c.fin - c.inicio)::NUMERIC(10, 3) AS duracion_seg,
    c.desfase_seg,
    c.registros_validos,
    c.registros_insertados,
    c.registros_validos - c.registros_insertados AS registros_duplicados,
    c.registros_rechazados,
    c.detalle
FROM ciclos_rt c;


-- Hechos: registros descartados por la validación
DROP VIEW IF EXISTS bi_rechazos;
CREATE VIEW bi_rechazos AS
SELECT
    r.id,
    r.ciclo_id,
    r.linea_id,
    SPLIT_PART(r.motivo, ':', 1) AS motivo,   -- sin el valor concreto, para agrupar
    r.motivo AS motivo_detalle,
    (r.extraido_en AT TIME ZONE 'Europe/Madrid')::DATE AS fecha
FROM rechazos_rt r;


-- Dimensión calendario: desde el primer dato registrado hasta hoy (hora de España)
DROP VIEW IF EXISTS bi_calendario;
CREATE VIEW bi_calendario AS
WITH limites AS (
    SELECT
        LEAST(
            (SELECT MIN((inicio AT TIME ZONE 'Europe/Madrid')::DATE) FROM ciclos_rt),
            (SELECT MIN((fecha_peticion AT TIME ZONE 'Europe/Madrid')::DATE) FROM bus_parada_rt),
            (NOW() AT TIME ZONE 'Europe/Madrid')::DATE
        ) AS desde,
        (NOW() AT TIME ZONE 'Europe/Madrid')::DATE AS hasta
)
SELECT
    d::DATE AS fecha,
    EXTRACT(YEAR FROM d)::INTEGER AS anio,
    EXTRACT(MONTH FROM d)::INTEGER AS mes_num,
    (ARRAY['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto',
           'Septiembre','Octubre','Noviembre','Diciembre'])[EXTRACT(MONTH FROM d)::INTEGER] AS mes,
    EXTRACT(DAY FROM d)::INTEGER AS dia,
    EXTRACT(ISODOW FROM d)::INTEGER AS dia_semana_num,
    (ARRAY['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'])[EXTRACT(ISODOW FROM d)::INTEGER] AS dia_semana,
    CASE WHEN EXTRACT(ISODOW FROM d) <= 5 THEN 'Laborable' ELSE 'Fin de semana' END AS tipo_dia
FROM limites, GENERATE_SERIES(limites.desde, limites.hasta, INTERVAL '1 day') AS d;


-- Dimensión horas del día, con franjas típicas de demanda en Coruña
DROP VIEW IF EXISTS bi_horas;
CREATE VIEW bi_horas AS
SELECT
    h AS hora,
    LPAD(h::TEXT, 2, '0') || ':00' AS hora_etiqueta,
    CASE
        WHEN h < 6 THEN 'Sin servicio'
        WHEN h < 10 THEN 'Punta mañana'
        WHEN h < 13 THEN 'Valle mañana'
        WHEN h < 16 THEN 'Punta mediodía'
        WHEN h < 21 THEN 'Tarde'
        ELSE 'Noche'
    END AS franja,
    h >= 6 AS en_ventana_captura
FROM GENERATE_SERIES(0, 23) AS h;
