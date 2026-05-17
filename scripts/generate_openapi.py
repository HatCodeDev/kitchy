import json
import codecs
import sys
import os

# Añadir el directorio raíz al path para poder importar main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

def generate_spec():
    spec = app.openapi()
    # Escribir en el directorio de la app Flutter
    target_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "app", "lib", "data", "api_spec", "openapi.json")
    print(f"Generando OpenAPI spec en: {target_path}")
    with codecs.open(target_path, "w", "utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    generate_spec()
