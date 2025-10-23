"""
Utilidades de cifrado para guardar tokens de acceso de forma segura.

Se utiliza `cryptography.fernet` para cifrar y descifrar cadenas. La clave
de cifrado se obtiene de la variable de entorno `TOKENS_SECRET_KEY`. Si
esta variable no está definida en tiempo de ejecución, se genera una
clave de forma automática. En un entorno de producción, deberías
definir explícitamente `TOKENS_SECRET_KEY` para asegurar que los tokens
persisten entre reinicios de la aplicación.
"""

import os
from cryptography.fernet import Fernet

_key = os.getenv("TOKENS_SECRET_KEY")
if not _key:
    # Genera una clave ad-hoc si no se define. Esto hace que los tokens
    # cifrados en una ejecución no puedan descifrarse en otra, por lo que
    # se recomienda siempre definir TOKENS_SECRET_KEY en entorno real.
    _key = Fernet.generate_key().decode()

# Aceptamos claves en formato base64 como cadena (las que devuelve Fernet) o
# directamente con el prefijo "gAAAA" (que indica un token ya generado). Si
# la clave ya incluye el prefijo de Fernet (gAAAA...), no la decodificamos.
_key_bytes = _key.encode() if not _key.startswith("gAAAA") else _key
fernet = Fernet(_key_bytes)


def encrypt_str(s: str) -> str:
    """Cifra una cadena de texto y la devuelve codificada en base64."""
    return fernet.encrypt(s.encode()).decode()


def decrypt_str(s: str) -> str:
    """Descifra una cadena cifrada y devuelve el texto en claro."""
    return fernet.decrypt(s.encode()).decode()