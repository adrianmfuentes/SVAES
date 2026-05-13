from slowapi import Limiter
from slowapi.util import get_remote_address

# Configuración del limitador utilizando la dirección IP del cliente como clave
limiter = Limiter(key_func=get_remote_address)
