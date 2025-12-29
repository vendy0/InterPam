from decimal import Decimal, ROUND_HALF_UP

# --- UTILITAIRES DE CONVERSION ---
def vers_centimes(montant):
    """Convertit un Decimal, float ou string en entier (centimes)"""
    if montant is None:
        return 0
    return int(
        (Decimal(str(montant)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def depuis_centimes(centimes):
    """Convertit un entier (centimes) en Decimal pour les calculs"""
    if centimes is None:
        return Decimal("0.00")
    return (Decimal(str(centimes)) / Decimal("100")).quantize(Decimal("0.01"))
