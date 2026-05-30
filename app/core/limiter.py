"""
Configuración del limitador de velocidad (Rate Limiting) para Kitchy API.

Este módulo inicializa una instancia global de SlowAPI utilizando la dirección IP
del cliente remoto como clave identificadora. Sirve para mitigar ataques DDoS,
prevenir el spam en endpoints sensibles (ej. autenticación) y asegurar la equidad en el uso del backend.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Instancia compartida del limitador de velocidad (Rate Limiter)
# Usamos la dirección IP del cliente remoto como clave de identificación
limiter = Limiter(key_func=get_remote_address)
