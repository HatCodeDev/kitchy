import pytest
from decimal import Decimal
from pydantic import ValidationError
from app.schemas.user_config import UserConfigUpdate


def test_user_config_update_valid():
    """Valida que acepte datos correctos y redondee o guarde Decimal."""
    config = UserConfigUpdate(
        empaque_mxn_default=Decimal("15.50"),
        desgaste_pct_default=Decimal("10.0")
    )
    assert config.empaque_mxn_default == Decimal("15.50")
    assert config.desgaste_pct_default == Decimal("10.0")


def test_user_config_update_optional_fields():
    """Valida que los campos sean opcionales y tengan None por defecto."""
    config = UserConfigUpdate()
    assert config.empaque_mxn_default is None
    assert config.desgaste_pct_default is None


def test_user_config_update_rejects_negative_empaque():
    """Valida que empaque_mxn_default rechace valores menores a 0."""
    with pytest.raises(ValidationError) as exc_info:
        UserConfigUpdate(empaque_mxn_default=Decimal("-0.01"))
    assert "greater than or equal to 0" in str(exc_info.value)


def test_user_config_update_rejects_invalid_desgaste():
    """Valida que desgaste_pct_default rechace valores fuera de [0, 100]."""
    with pytest.raises(ValidationError) as exc_info:
        UserConfigUpdate(desgaste_pct_default=Decimal("-1"))
    assert "greater than or equal to 0" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        UserConfigUpdate(desgaste_pct_default=Decimal("100.01"))
    assert "less than or equal to 100" in str(exc_info.value)
