"""Security helpers for the expiry module."""

import base64
import hashlib
import hmac
import os
import secrets


PASSWORD_ITERATIONS = 120000
SECRET_FILENAME = '.expiry_secret'


def ensure_app_secret(base_dir):
    """Create and return the app secret used for SMTP password encryption."""
    secret_path = os.path.join(base_dir, SECRET_FILENAME)
    if not os.path.exists(secret_path):
        secret = secrets.token_hex(32)
        with open(secret_path, 'w', encoding='utf-8') as f:
            f.write(secret)
        try:
            os.chmod(secret_path, 0o600)
        except OSError:
            pass
        return secret, True
    with open(secret_path, 'r', encoding='utf-8') as f:
        secret = f.read().strip()
    if not secret:
        secret = secrets.token_hex(32)
        with open(secret_path, 'w', encoding='utf-8') as f:
            f.write(secret)
        return secret, True
    return secret, False


def hash_password(password, salt=None):
    """Hash a password using PBKDF2."""
    if salt is None:
        salt = secrets.token_bytes(16)
    elif isinstance(salt, str):
        salt = bytes.fromhex(salt)
    digest = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        PASSWORD_ITERATIONS,
    )
    return '{}${}'.format(salt.hex(), digest.hex())


def verify_password(password, stored_hash):
    """Check a password against the stored PBKDF2 hash."""
    if not stored_hash or '$' not in stored_hash:
        return False
    salt_hex, expected_hex = stored_hash.split('$', 1)
    actual = hash_password(password, salt_hex)
    return hmac.compare_digest(actual, '{}${}'.format(salt_hex, expected_hex))


def _derive_key(secret):
    return hashlib.sha256(secret.encode('utf-8')).digest()


def _keystream(key, length):
    chunks = []
    counter = 0
    while len(b''.join(chunks)) < length:
        block = hmac.new(key, 'expiry-{}'.format(counter).encode('utf-8'), hashlib.sha256).digest()
        chunks.append(block)
        counter += 1
    return b''.join(chunks)[:length]


def encrypt_secret(plain_text, secret):
    """Encrypt SMTP passwords using a simple symmetric stream plus HMAC tag."""
    if not plain_text:
        return ''
    data = plain_text.encode('utf-8')
    key = _derive_key(secret)
    cipher = bytes(a ^ b for a, b in zip(data, _keystream(key, len(data))))
    tag = hmac.new(key, cipher, hashlib.sha256).hexdigest().encode('ascii')
    return base64.urlsafe_b64encode(tag + b':' + cipher).decode('ascii')


def decrypt_secret(cipher_text, secret):
    """Decrypt SMTP passwords; return empty string when data is missing/corrupt."""
    if not cipher_text:
        return ''
    try:
        raw = base64.urlsafe_b64decode(cipher_text.encode('ascii'))
        tag, cipher = raw.split(b':', 1)
    except Exception:
        return ''
    key = _derive_key(secret)
    expected = hmac.new(key, cipher, hashlib.sha256).hexdigest().encode('ascii')
    if not hmac.compare_digest(tag, expected):
        return ''
    plain = bytes(a ^ b for a, b in zip(cipher, _keystream(key, len(cipher))))
    return plain.decode('utf-8')

