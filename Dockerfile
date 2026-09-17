# Actualizamos a Python 3.12 para que coincida con tus librerías locales
FROM python:3.12-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos dependencias del sistema necesarias para compilar/conectar con PostgreSQL
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiamos e instalamos los requerimientos de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código fuente del proyecto al contenedor
COPY . .

# Comando por defecto para ejecutar el orquestador
CMD ["python3", "src/scheduler.py"]