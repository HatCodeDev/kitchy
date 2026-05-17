from slowapi import Limiter
from slowapi.util import get_remote_address

# Instancia compartida del limitador de velocidad (Rate Limiter)
# Usamos la dirección IP del cliente remoto como clave de identificación
limiter = Limiter(key_func=get_remote_address)
