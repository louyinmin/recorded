"""Security helpers for life backend."""

import hashlib
import hmac
import secrets


PASSWORD_ITERATIONS = 120000


def hash_password(password, salt=None):
    """Hash password using PBKDF2."""
    if salt is None:
        salt = secrets.token_bytes(16)
    elif isinstance(salt, str):
        salt = bytes.fromhex(salt)
    digest = hashlib.pbkdf2_hmac(
        'sha256',
        str(password or '').encode('utf-8'),
        salt,
        PASSWORD_ITERATIONS,
    )
    return '{}${}'.format(salt.hex(), digest.hex())


def verify_password(password, stored_hash):
    """Verify PBKDF2 hash."""
    if not stored_hash or '$' not in stored_hash:
        return False
    salt_hex, digest_hex = stored_hash.split('$', 1)
    actual = hash_password(password, salt_hex)
    return hmac.compare_digest(actual, '{}${}'.format(salt_hex, digest_hex))

