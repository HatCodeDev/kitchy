"""
Utilidad de Integración con WhatsApp.

Este módulo provee funciones utilitarias para procesar números telefónicos y generar
enlaces directos (Deep Links) que faciliten la comunicación con los clientes a través de WhatsApp.
"""
import re
from typing import Optional


def build_whatsapp_url(numero: Optional[str]) -> Optional[str]:
    """
    Toma un número de teléfono crudo, lo limpia y construye el Deep Link oficial de WhatsApp.

    Realiza labores de normalización de cadenas, remueve caracteres no numéricos y asume el código de
    país de México (+52) si el número recibido consta únicamente de los 10 dígitos locales.

    Args:
        numero (Optional[str]): Cadena de caracteres que representa el número telefónico del cliente.
                                Puede contener espacios, guiones, símbolos de suma o paréntesis.

    Returns:
        Optional[str]: URL absoluta de redirección directa a WhatsApp (`https://wa.me/...`) o
                       `None` si el parámetro de entrada es inválido o no cumple con el patrón requerido.

    Examples:
        >>> build_whatsapp_url("55 1234-5678")
        "https://wa.me/525512345678"
        >>> build_whatsapp_url("+52 55 (1234) 5678")
        "https://wa.me/525512345678"
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