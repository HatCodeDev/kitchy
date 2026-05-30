"""
Servicio de Conversión de Unidades de Medida.

Este módulo provee lógica para convertir cantidades físicas entre diferentes unidades
de masa (g, kg, oz, lb), volumen (ml, l, gal, tz, cda, cdita), unidades discretas
(piezas, docenas) y tiempo (seg, min, h).
"""
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class UnitConversionService:
    """
    Servicio encargado de realizar conversiones de unidades y determinar tipos de medidas.

    Atributos:
        CONVERSION_FACTORS (dict): Diccionario que define los factores de multiplicación
            para llevar cualquier unidad a su respectiva unidad base (gr para masa, ml
            para volumen, pza para discretos, seg para tiempo).
        DISCRETE_UNITS (set): Conjunto de cadenas que representan unidades individuales discretas.
    """
    # Factores de conversión hacia una unidad base.
    # Masa: base 'gr'
    # Volumen: base 'ml'
    # Piezas: base 'pza'
    
    CONVERSION_FACTORS = {
        # Masa (base: gr)
        'gr': Decimal('1'),
        'g': Decimal('1'),
        'kg': Decimal('1000'),
        'mg': Decimal('0.001'),
        'oz': Decimal('28.3495'),
        'lb': Decimal('453.592'),
        
        # Volumen (base: ml)
        'ml': Decimal('1'),
        'l': Decimal('1000'),
        'lt': Decimal('1000'),
        'gal': Decimal('3785.41'),
        'oz_fl': Decimal('29.5735'),
        'tz': Decimal('240'),
        'cda': Decimal('15'),
        'cdita': Decimal('5'),
        
        # Unidades discretas (base: pza)
        'pza': Decimal('1'),
        'docena': Decimal('12'),

        # Tiempo (base: seg)
        'seg': Decimal('1'),
        's': Decimal('1'),
        'min': Decimal('60'),
        'm': Decimal('60'),
        'h': Decimal('3600'),
        'hr': Decimal('3600'),
    }

    DISCRETE_UNITS = {'pza', 'pzas', 'pieza', 'piezas', 'unidad', 'unidades'}

    @staticmethod
    def es_unidad_discreta(unidad: str) -> bool:
        """
        Determina si una unidad representa piezas o unidades discretas enteras.

        Args:
            unidad (str): El nombre o abreviatura de la unidad a evaluar.

        Returns:
            bool: True si la unidad es discreta (ej. pieza, docena), False en caso contrario.
        """
        if not unidad:
            return False
        return unidad.lower().strip() in UnitConversionService.DISCRETE_UNITS

    @staticmethod
    def convertir(cantidad: Decimal, unidad_origen: str, unidad_destino: str) -> Decimal:
        """
        Convierte una magnitud de una unidad física de origen a una de destino.

        La conversión se realiza en dos etapas: primero se lleva la cantidad a la
        unidad base correspondiente y luego se convierte de la unidad base a la de destino.

        Args:
            cantidad (Decimal): El valor numérico a convertir.
            unidad_origen (str): La unidad en la que está expresada la cantidad inicial.
            unidad_destino (str): La unidad deseada para el resultado final.

        Returns:
            Decimal: El valor equivalente en la unidad de destino. Si alguna unidad
                no es reconocida, retorna la cantidad original y registra un warning.
        """
        if not unidad_origen or not unidad_destino:
            return cantidad

        u_origen = unidad_origen.lower().strip()
        u_destino = unidad_destino.lower().strip()

        if u_origen == u_destino:
            return cantidad
            
        factor_origen = UnitConversionService.CONVERSION_FACTORS.get(u_origen)
        factor_destino = UnitConversionService.CONVERSION_FACTORS.get(u_destino)

        if factor_origen is None or factor_destino is None:
            logger.warning(f"Unidades no reconocidas para conversión: {u_origen} a {u_destino}")
            return cantidad

        # 1. Llevar a unidad base (ej. kg -> gr)
        cantidad_base = cantidad * factor_origen
        
        # 2. Llevar de unidad base a destino (ej. gr -> oz)
        cantidad_final = cantidad_base / factor_destino

        return cantidad_final
