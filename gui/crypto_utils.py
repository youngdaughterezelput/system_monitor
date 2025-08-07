# crypto_utils.py
from cryptography.fernet import Fernet
import base64
import os


class SecretManager:
    def __init__(self, key_file='secret.key'):
        self.key_file = key_file
        self.key = self._load_or_generate_key()
        self.cipher = Fernet(self.key)

    def _load_or_generate_key(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()
        key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(key)
        os.chmod(self.key_file, 0o600)  # Только для владельца
        return key

    def encrypt(self, text: str) -> str:
        return self.cipher.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        return self.cipher.decrypt(encrypted_text.encode()).decode()