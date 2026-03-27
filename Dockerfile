# Imagen oficial de Python ligera (slim) por seguridad y rendimiento.
FROM python:3.12-slim

# Establecemos el directorio de trabajo dentro del contenedor.
WORKDIR /app

# Copiamos el archivo de requerimientos.
# Esto aprovecha la caché de Docker para no reinstalar todo si solo cambiaste código en main.py.
COPY requirements.txt .

# Instalamos las dependencias de Python.
# --no-cache-dir evita guardar archivos temporales, manteniendo el contenedor liviano y seguro.
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código de nuestra app al contenedor.
COPY . .

# Exponemos el puerto por donde se comunicará FastAPI.
EXPOSE 8000

# El comando que ejecutará el contenedor al encenderse.
# Usamos 0.0.0.0 para que escuche conexiones desde fuera del contenedor.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]