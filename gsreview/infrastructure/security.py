"""Criptografía local: nunca entrega secretos mediante funciones administrativas."""

import hashlib
import os
import secrets
from pathlib import Path
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from cryptography.fernet import Fernet

PASSWORDS = PasswordHasher(type=Type.ID)
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def matches(encoded, value):
    try:
        return PASSWORDS.verify(encoded, value)
    except (VerificationError, InvalidHashError):
        return False


class LocalCipher:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "wb") as f:
                f.write(Fernet.generate_key())
        self.fernet = Fernet(self.path.read_bytes())

    def encrypt(self, value):
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, value):
        return self.fernet.decrypt(value.encode()).decode()
