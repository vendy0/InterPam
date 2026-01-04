from utils.finance import vers_centimes, depuis_centimes
from decimal import Decimal

def test_conversions_financieres():
    # Test de conversion vers centimes
    assert vers_centimes(10.25) == 1025
    assert vers_centimes("10.25") == 1025
    assert vers_centimes(Decimal("10.25")) == 1025
    
    # Test d'arrondi (ROUND_HALF_UP)
    assert vers_centimes(10.256) == 1026
    
    # Test retour en Decimal
    assert depuis_centimes(1025) == Decimal("10.25")
    assert depuis_centimes(0) == Decimal("0.00")
