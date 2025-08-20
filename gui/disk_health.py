import subprocess
import platform
import re
from dataclasses import dataclass
from typing import Dict, Optional
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

@dataclass
class SmartAttribute:
    id: int
    name: str
    value: int
    worst: int
    threshold: int
    raw: str
    type: str

@dataclass
class DiskHealth:
    model: str
    serial: str
    temperature: Optional[float]
    power_on_hours: Optional[float]
    bad_sectors: int
    attributes: Dict[str, SmartAttribute]
    lifespan: Optional[float]
    health_status: str = "Unknown"  # Новое поле для общего статуса здоровья

class DiskHealthAnalyzer:
    def __init__(self):
        self.system = platform.system()
        self.smartctl_path = self._find_smartctl()
        self.wmi_available = False
        
        if self.system == "Windows":
            try:
                # Проверка доступности модуля wmi
                import wmi
                self.wmi = wmi.WMI()
                self.wmi_available = True
                logger.info("WMI доступен для анализа дисков в Windows")
            except ImportError:
                logger.warning("Для расширенного анализа в Windows установите pywin32: pip install pywin32")
            except Exception as e:
                logger.error(f"Ошибка при инициализации WMI: {e}")
                self.wmi_available = False

    def _find_smartctl(self):
        try:
            if platform.system() == "Windows":
                # Проверяем наличие smartctl.exe в PATH
                result = subprocess.run(
                    ["where", "smartctl"], 
                    capture_output=True, 
                    text=True, 
                    check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    return "smartctl"
                return None
            else:
                subprocess.run(
                    ["smartctl", "--version"], 
                    check=True, 
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return "smartctl"
        except Exception:
            return None

    def get_health(self, device: str) -> Optional[DiskHealth]:
        system = platform.system()
        
        if system == "Darwin":  # macOS
            return self._get_health_macos(device)
        elif system == "Linux" and self.smartctl_path:
            return self._get_health_smartctl(device)
        elif system == "Windows":
            if self.smartctl_path:
                return self._get_health_smartctl(device)
            elif self.wmi_available:
                return self._get_health_wmi(device)
        return None
    
    def _get_health_macos(self, device: str) -> Optional[DiskHealth]:
        """Получение информации о здоровье диска на macOS"""
        try:
            # Используем diskutil для получения основной информации
            info_output = subprocess.run(
                ["diskutil", "info", device],
                capture_output=True,
                text=True,
                check=True
            ).stdout
            
            # Используем smartctl если доступен
            if self.smartctl_path:
                smart_output = subprocess.run(
                    [self.smartctl_path, "-A", "-i", device],
                    capture_output=True,
                    text=True,
                    check=False
                ).stdout
                return self._parse_smartctl(smart_output)
            else:
                return self._parse_diskutil(info_output)
                
        except Exception as e:
            logger.error(f"Ошибка получения здоровья диска на macOS для {device}: {str(e)}")
            return None
        
    def _parse_diskutil(self, output: str) -> DiskHealth:
        """Парсинг вывода diskutil для macOS"""
        model_match = re.search(r"Device / Media Name:\s+(.+)", output)
        size_match = re.search(r"Disk Size:\s+([\d.]+ [A-Za-z]+)", output)
        
        return DiskHealth(
            model=model_match.group(1) if model_match else "Unknown",
            serial="N/A",  # На macOS сложнее получить серийный номер
            temperature=None,
            power_on_hours=None,
            bad_sectors=0,
            attributes={},
            lifespan=None,
            health_status="N/A (требуется smartmontools)"
        )

    def _get_health_smartctl(self, device: str) -> Optional[DiskHealth]:
        try:
            if self.system == "Windows":
                # Преобразуем букву диска в формат, понятный smartctl
                if len(device) >= 2 and device[1] == ":":
                    device = f"\\\\.\\{device[0]}:"
                else:
                    # Пробуем использовать как есть
                    pass
                    
            output = subprocess.run(
                [self.smartctl_path, "-A", "-i", device],
                capture_output=True,
                text=True,
                check=True
            ).stdout
            return self._parse_smartctl(output)
        except Exception as e:
            logger.error(f"Ошибка smartctl для {device}: {str(e)}")
            return None

    def _get_health_wmi(self, device: str) -> Optional[DiskHealth]:
        """Получение информации о здоровье диска через WMI в Windows"""
        try:
            if not self.wmi_available:
                return None
                
            # Убираем двоеточие и слеши для поиска по букве диска
            drive_letter = device[0] if device and device[0].isalpha() else None
            if not drive_letter:
                return None

            # Получаем информацию о физическом диске
            for disk in self.wmi.Win32_DiskDrive():
                for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                    for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
                        if logical_disk.DeviceID == f"{drive_letter}:":
                            # Основная информация о диске
                            model = disk.Model
                            serial = disk.SerialNumber.strip() if disk.SerialNumber else "Unknown"
                            
                            # Собираем атрибуты SMART через WMI
                            attributes = {}
                            try:
                                # Этот блок зависит от конкретной реализации WMI
                                # В упрощенной версии просто возвращаем основную информацию
                                pass
                            except Exception as e:
                                logger.error(f"Ошибка получения SMART через WMI: {e}")
                            
                            return DiskHealth(
                                model=model,
                                serial=serial,
                                temperature=None,
                                power_on_hours=None,
                                bad_sectors=0,
                                attributes=attributes,
                                lifespan=None,
                                health_status="N/A"
                            )
            return None
        except Exception as e:
            logger.error(f"Ошибка WMI для {device}: {str(e)}")
            return None

    def _parse_smartctl(self, output: str) -> DiskHealth:
        model_match = re.search(r"Device Model:\s+(.+)\n", output)
        serial_match = re.search(r"Serial Number:\s+(.+)\n", output)
        health_match = re.search(r"SMART overall-health self-assessment test result:\s+(.+)", output)
        
        attributes = {}
        for match in re.finditer(
            r"(\d+)\s+(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d-]+)\s+(\S+)\s+(.+)", 
            output
        ):
            attr = SmartAttribute(
                id=int(match.group(1)),
                name=match.group(2),
                value=int(match.group(3)),
                worst=int(match.group(4)),
                threshold=int(match.group(5)),
                raw=match.group(6),
                type=match.group(8)
            )
            attributes[attr.name] = attr

        # Определение общего статуса здоровья
        health_status = health_match.group(1).strip() if health_match else "Unknown"
        
        return DiskHealth(
            model=model_match.group(1) if model_match else "Unknown",
            serial=serial_match.group(1) if serial_match else "Unknown",
            temperature=self._parse_temperature(attributes.get("Temperature_Celsius")),
            power_on_hours=self._parse_power_hours(attributes.get("Power_On_Hours")),
            bad_sectors=int(attributes.get("Reallocated_Sector_Ct").raw) if attributes.get("Reallocated_Sector_Ct") else 0,
            attributes=attributes,
            lifespan=self._calculate_ssd_lifespan(attributes),
            health_status=health_status
        )

    def _parse_temperature(self, attr: Optional[SmartAttribute]) -> Optional[float]:
        if not attr:
            return None
        try:
            return float(attr.raw)
        except (ValueError, TypeError):
            return None

    def _parse_power_hours(self, attr: Optional[SmartAttribute]) -> Optional[float]:
        if not attr:
            return None
        try:
            return float(attr.raw)
        except (ValueError, TypeError):
            return None

    def _calculate_ssd_lifespan(self, attributes: Dict[str, SmartAttribute]) -> Optional[float]:
        if wear_level := attributes.get("Wear_Leveling_Count"):
            try:
                return (wear_level.value / wear_level.threshold) * 100
            except (TypeError, ZeroDivisionError):
                return None
        return None