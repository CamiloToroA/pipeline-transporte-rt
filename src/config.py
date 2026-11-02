import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "adminpassword")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "transporte_db")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

RT_URL = "https://itranvias.com/queryitr_v3.php"

# Muestra de líneas por tipología (route_id del GTFS estático), elegidas por
# frecuencia y cobertura en servicio de lunes a viernes. Se guarda en dim_linea.
TIPOLOGIAS = {
    "100": "Troncal céntrica",              # 1   Abente y Lago-Castrillón (serie original)
    "400": "Troncal alta frecuencia",       # 4   Av. Hércules-Barrio das Flores
    "2450": "Lanzadera universitaria",      # UDC Pra.Pontevedra-Elviña-UDC, la más frecuente
    "1200": "Servicio hospitalario",        # 12  Os Rosales-CHUAC-Materno
    "2300": "Periférica baja frecuencia",   # 23  Abente y Lago-Breogán
}
LINEAS = [l.strip() for l in os.getenv("LINEAS", ",".join(TIPOLOGIAS)).split(",") if l.strip()]

ZONA_ESPAÑA = ZoneInfo("Europe/Madrid")

# Rutas absolutas para que funcione igual en Docker (/app) y en WSL
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_DIR = os.path.join(BASE_DIR, "sql")
ROUTES_PATH = os.path.join(BASE_DIR, "data_extracted", "routes.txt")
STOPS_PATH = os.path.join(BASE_DIR, "data_extracted", "stops.txt")
