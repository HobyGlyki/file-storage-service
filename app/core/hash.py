import hashlib
import os

SALT = os.getenv("SECRET_SALT")


def get_password_hash(password: str):
    salted_password = f"{password}{SALT}"
    print(password)
    return hashlib.sha256(salted_password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str):
    return get_password_hash(plain_password) == hashed_password
