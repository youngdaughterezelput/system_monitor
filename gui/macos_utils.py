# macos_utils.py
import subprocess
import platform
import re

class MacOSDiskUtils:
    @staticmethod
    def get_physical_disks():
        """Получение списка физических дисков на macOS"""
        try:
            result = subprocess.run(
                ["diskutil", "list", "-plist"],
                capture_output=True,
                text=True,
                check=True
            )
            # Парсинг plist вывода для получения информации о дисках
            return result.stdout
        except Exception as e:
            print(f"Ошибка получения списка дисков: {e}")
            return None
    
    @staticmethod
    def get_apfs_containers():
        """Получение информации о APFS контейнерах"""
        try:
            result = subprocess.run(
                ["diskutil", "apfs", "list"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except Exception as e:
            print(f"Ошибка получения APFS информации: {e}")
            return None