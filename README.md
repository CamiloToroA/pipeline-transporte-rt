# Pipeline de Transporte Público en Tiempo Real (GTFS-RT)

Pipeline de Ingeniería de Datos para la ingesta, procesamiento y almacenamiento de posiciones de transporte público en tiempo real.

## Tech Stack
* **Entorno:** WSL 2 (Ubuntu)
* **Lenguaje:** Python 3 (Pandas, SQLAlchemy)
* **Base de Datos:** PostgreSQL 15 (Docker)
* **Contenedores:** Docker Compose

## Estado del Proyecto
- [x] Configuración del entorno de desarrollo y Docker.
- [x] Despliegue de base de datos PostgreSQL local.
- [x] Script de ingesta base y validación de conexión DB.
- [x] Integración con API de transporte en tiempo real.
- [x] Transformaciones de datos y orquestación.
- [x] Desarrollar Base de Datos.
- [x] Desarrollar capa Analítica .
- [x] Desarrollo Tablero Power BI.

## Ingesta en tiempo real

**Líneas monitoreadas** (`route_id`, configurable con la variable `LINEAS`), elegidas por tipología a partir del GTFS estático (servicio de lunes a viernes):

| route_id | Línea | Tipología | Viajes/día | Paradas |
|---|---|---|---|---|
| 100 | 1 · Abente y Lago–Castrillón | Troncal céntrica (serie original) | 104 | 34 |
| 400 | 4 · Av. Hércules–Barrio das Flores | Troncal de alta frecuencia | 148 | 47 |
| 2450 | UDC · Pza. Pontevedra–Elviña–UDC | Lanzadera universitaria | 292 | 29 |
| 1200 | 12 · Os Rosales–CHUAC–Materno | Servicio hospitalario | 72 | 48 |
| 2300 | 23 · Abente y Lago–Breogán | Periférica de baja frecuencia | 25 | 58 |

La API limita a 1 consulta/s, 4/min, 199/h y 1999/día, así que las consultas se espacian para usar el 95 % de la cuota diaria (una cada ~34 s; cada línea se actualiza cada ~2,8 min). Ante un 429 el scheduler deja de consultar y pausa 5 min, duplicando la pausa hasta 1 h mientras siga bloqueado. El scheduler opera de 06:00 a 00:00 hora de España; el contenedor puede quedar encendido 24/7.

**Tablas** (`sql/schema.sql`, se crean solas al arrancar):
- `bus_parada_rt`: observaciones válidas, con `UNIQUE` para evitar duplicados y fechas `TIMESTAMPTZ`.
- `ciclos_rt`: bitácora de cada consulta (OK, VACIO, ERROR_*), para medir la completitud.
- `rechazos_rt`: registros descartados por validación, con motivo y dato original.

**Pruebas:** `venv/bin/python -m unittest discover -s tests -v`

**Borrar la tabla antigua** (`line_status_rt`, del esquema anterior), con el pipeline nuevo ya levantado:
`docker exec -it postgres_transporte psql -U admin -d transporte_db -c "DROP TABLE IF EXISTS line_status_rt;"`

## Tablero Power BI

Proyecto PBIP (modelo TMDL + reporte PBIR, archivos de texto) generado con `powerbi/generar_tablero.py`:
`python3 powerbi/generar_tablero.py <carpeta_salida> <carpeta StaticResources del tema>`.
Lee las vistas `bi_*`, `dim_linea` y `dim_parada`; los parámetros `Servidor` y `BaseDatos` apuntan a `localhost` / `transporte_db`.
