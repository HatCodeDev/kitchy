from decimal import Decimal
from app.models.user import User

def test_user_defaults():
    """Verifica que un nuevo usuario tenga los valores por defecto correctos."""
    user = User()
    assert user.plan == "free"
    assert user.empaque_mxn_default == Decimal("0.00")
    assert user.desgaste_pct_default == Decimal("0.00")

def test_user_custom_values():
    """Verifica que se puedan asignar valores personalizados."""
    user = User(
        plan="premium",
        empaque_mxn_default=Decimal("15.50"),
        desgaste_pct_default=Decimal("5.00")
    )
    assert user.plan == "premium"
    assert user.empaque_mxn_default == Decimal("15.50")
    assert user.desgaste_pct_default == Decimal("5.00")
