import re
from typing import Optional


def build_whatsapp_url(numero: Optional[str]) -> Optional[str]:
    """
    Toma un número de teléfono crudo, lo limpia y construye el Deep Link de WhatsApp.
    Si el número es inválido, retorna None silenciosamente sin romper el servidor.
    """
    if not numero:
        return None

    # 1. Limpiar la "basura" visual: espacios, guiones y paréntesis
    numero_limpio = re.sub(r'[\s\-\(\)]', '', numero)

    # 2. Quitar el '+' si el usuario lo copió y pegó (ej. +52...)
    if numero_limpio.startswith('+'):
        numero_limpio = numero_limpio[1:]

    # 3. Si no empieza con '52' (código de México), se lo agregamos asumiendo que es local
    if not numero_limpio.startswith('52'):
        numero_limpio = f"52{numero_limpio}"

    # 4. Verificación estricta: Debe ser '52' seguido de exactamente 10 dígitos
    if not re.match(r'^52[0-9]{10}$', numero_limpio):
        return None

    # 5. Construir y retornar la URL final
    return f"https://wa.me/{numero_limpio}"