from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class UnitConversionService:
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
    }

    @staticmethod
    def convertir(cantidad: Decimal, unidad_origen: str, unidad_destino: str) -> Decimal:
        """
        Convierte una cantidad de una unidad origen a una unidad destino.
        Ejemplo: convertir(500, 'gr', 'kg') -> 0.5
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
