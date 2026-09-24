-- Vistas analíticas para el pipeline de transporte en tiempo real

-- 1. Flota activa por hora (para ver cuántos buses circulan en la red)
CREATE OR REPLACE VIEW v_flota_activa_hora AS
SELECT 
    DATE_TRUNC('hour', 
        (SUBSTRING(fecha_peticion, 1, 4) || '-' || 
         SUBSTRING(fecha_peticion, 5, 2) || '-' || 
         SUBSTRING(fecha_peticion, 7, 2) || ' ' || 
         SUBSTRING(fecha_peticion, 9, 2) || ':' || 
         SUBSTRING(fecha_peticion, 11, 2) || ':' || 
         SUBSTRING(fecha_peticion, 13, 2))::TIMESTAMP
    ) AS hora_registro,
    COUNT(DISTINCT bus_id) AS total_buses_activos,
    COUNT(DISTINCT parada_id) AS paradas_con_actividad,
    COUNT(*) AS total_registros
FROM 
    line_status_rt
GROUP BY 
    1
ORDER BY 
    hora_registro DESC;


-- 2. Paradas con mayor movimiento o afluencia de buses
CREATE OR REPLACE VIEW v_top_paradas_frecuentes AS
SELECT 
    parada_id,
    sentido,
    COUNT(DISTINCT bus_id) AS total_buses_unicos,
    COUNT(*) AS total_interacciones,
    MAX(
        (SUBSTRING(fecha_peticion, 1, 4) || '-' || 
         SUBSTRING(fecha_peticion, 5, 2) || '-' || 
         SUBSTRING(fecha_peticion, 7, 2) || ' ' || 
         SUBSTRING(fecha_peticion, 9, 2) || ':' || 
         SUBSTRING(fecha_peticion, 11, 2) || ':' || 
         SUBSTRING(fecha_peticion, 13, 2))::TIMESTAMP
    ) AS ultimo_reporte
FROM 
    line_status_rt
GROUP BY 
    parada_id, 
    sentido
ORDER BY 
    total_interacciones DESC;


-- 3. Resumen diario para validar que el pipeline y el scheduler corren bien
CREATE OR REPLACE VIEW v_salud_pipeline_diario AS
SELECT 
    DATE(
        (SUBSTRING(fecha_peticion, 1, 4) || '-' || 
         SUBSTRING(fecha_peticion, 5, 2) || '-' || 
         SUBSTRING(fecha_peticion, 7, 2) || ' ' || 
         SUBSTRING(fecha_peticion, 9, 2) || ':' || 
         SUBSTRING(fecha_peticion, 11, 2) || ':' || 
         SUBSTRING(fecha_peticion, 13, 2))::TIMESTAMP
    ) AS fecha,
    COUNT(*) AS total_registros,
    COUNT(DISTINCT bus_id) AS total_buses,
    MIN(
        (SUBSTRING(fecha_peticion, 1, 4) || '-' || 
         SUBSTRING(fecha_peticion, 5, 2) || '-' || 
         SUBSTRING(fecha_peticion, 7, 2) || ' ' || 
         SUBSTRING(fecha_peticion, 9, 2) || ':' || 
         SUBSTRING(fecha_peticion, 11, 2) || ':' || 
         SUBSTRING(fecha_peticion, 13, 2))::TIMESTAMP
    ) AS inicio_captura,
    MAX(
        (SUBSTRING(fecha_peticion, 1, 4) || '-' || 
         SUBSTRING(fecha_peticion, 5, 2) || '-' || 
         SUBSTRING(fecha_peticion, 7, 2) || ' ' || 
         SUBSTRING(fecha_peticion, 9, 2) || ':' || 
         SUBSTRING(fecha_peticion, 11, 2) || ':' || 
         SUBSTRING(fecha_peticion, 13, 2))::TIMESTAMP
    ) AS fin_captura
FROM 
    line_status_rt
GROUP BY 
    DATE(
        (SUBSTRING(fecha_peticion, 1, 4) || '-' || 
         SUBSTRING(fecha_peticion, 5, 2) || '-' || 
         SUBSTRING(fecha_peticion, 7, 2) || ' ' || 
         SUBSTRING(fecha_peticion, 9, 2) || ':' || 
         SUBSTRING(fecha_peticion, 11, 2) || ':' || 
         SUBSTRING(fecha_peticion, 13, 2))::TIMESTAMP
    )
ORDER BY 
    fecha DESC;