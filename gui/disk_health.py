import subprocess
import platform
import re
from dataclasses import dataclass
from typing import Dict, Optional

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

class DiskHealthAnalyzer:
    def __init__(self):
        self.smartctl_path = self._find_smartctl()

    def _find_smartctl(self):
        try:
            subprocess.run(["smartctl", "--version"], check=True, capture_output=True)
            return "smartctl"
        except Exception:
            return None

    def get_health(self, device: str) -> Optional[DiskHealth]:
        if not self.smartctl_path or platform.system() != "Linux":
            return None

        try:
            output = subprocess.run(
                [self.smartctl_path, "-A", "-i", device],
                capture_output=True,
                text=True,
                check=True
            ).stdout
            return self._parse_smartctl(output)
        except Exception:
            return None

    def _parse_smartctl(self, output: str) -> DiskHealth:
        model_match = re.search(r"Device Model:\s+(.+)\n", output)
        serial_match = re.search(r"Serial Number:\s+(.+)\n", output)
        
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

        return DiskHealth(
            model=model_match.group(1) if model_match else "Unknown",
            serial=serial_match.group(1) if serial_match else "Unknown",
            temperature=self._parse_temperature(attributes.get("Temperature_Celsius")),
            power_on_hours=self._parse_power_hours(attributes.get("Power_On_Hours")),
            bad_sectors=int(attributes.get("Reallocated_Sector_Ct").raw) if attributes.get("Reallocated_Sector_Ct") else 0,
            attributes=attributes,
            lifespan=self._calculate_ssd_lifespan(attributes)
        )

    def _parse_temperature(self, attr: Optional[SmartAttribute]) -> Optional[float]:
        return float(attr.raw) if attr else None

    def _parse_power_hours(self, attr: Optional[SmartAttribute]) -> Optional[float]:
        return float(attr.raw) if attr else None

    def _calculate_ssd_lifespan(self, attributes: Dict[str, SmartAttribute]) -> Optional[float]:
        if wear_level := attributes.get("Wear_Leveling_Count"):
            return (wear_level.value / wear_level.threshold) * 100
        return None