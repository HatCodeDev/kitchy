from app.utils.whatsapp import build_whatsapp_url

def test_whatsapp_url_10_digits():
    """Prueba con un número local común de 10 dígitos."""
    assert build_whatsapp_url("5512345678") == "https://wa.me/525512345678"
    # Prueba con formato humano que el usuario podría teclear
    assert build_whatsapp_url("(55) 1234-5678") == "https://wa.me/525512345678"

def test_whatsapp_url_with_52():
    """Prueba con el código de país ya incluido."""
    assert build_whatsapp_url("+525512345678") == "https://wa.me/525512345678"
    assert build_whatsapp_url("525512345678") == "https://wa.me/525512345678"

def test_whatsapp_url_none_or_empty():
    """Prueba de robustez: no debe romper la app si recibe nulos."""
    assert build_whatsapp_url(None) is None
    assert build_whatsapp_url("") is None
    assert build_whatsapp_url("   ") is None

def test_whatsapp_url_invalid():
    """Prueba de rechazo: si meten letras o un número incompleto, retorna None."""
    assert build_whatsapp_url("abc123def4") is None
    assert build_whatsapp_url("12345") is None  # Muy corto