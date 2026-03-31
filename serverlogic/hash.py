import hashlib

def get_password_hash(password: str):
    # Используем соль, чтобы хэш было сложнее взломать
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str):
    return get_password_hash(plain_password) == hashed_password