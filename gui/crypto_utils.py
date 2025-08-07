import os
import sys
import json
from cryptography.fernet import Fernet
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QComboBox, QCheckBox, QPushButton, QMessageBox)


class SecretManager:
    def __init__(self, key_file=None):
        self.key_file = key_file or self.get_default_key_path()
        self.key = self._load_or_generate_key()
        self.cipher = Fernet(self.key)

    def get_default_key_path(self):
        """Определяем путь к ключу в зависимости от режима"""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, 'secret.key')

    def _load_or_generate_key(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()

        key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(key)
        os.chmod(self.key_file, 0o600)
        return key

    def encrypt(self, text: str) -> str:
        return self.cipher.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        return self.cipher.decrypt(encrypted_text.encode()).decode()