from pywebpush import webpush
import base64

# Dans les versions récentes, on utilise cette méthode 
# ou on génère manuellement via cryptography
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

def generate_vapid_keys():
    # Génère une courbe elliptique (standard VAPID)
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Extraction de la clé privée au format DER puis Base64
    private_der = private_key.private_numbers().private_value.to_bytes(32, 'big')
    private_base64 = base64.urlsafe_b64encode(private_der).decode('utf-8').strip("=")

    # Extraction de la clé publique au format X9.62 (non compressé)
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    public_base64 = base64.urlsafe_b64encode(public_bytes).decode('utf-8').strip("=")

    print(f"Clé Privée (à garder secrète dans Python) :\n{private_base64}\n")
    print(f"Clé Publique (à mettre dans ton JS) :\n{public_base64}")

if __name__ == "__main__":
    generate_vapid_keys()

