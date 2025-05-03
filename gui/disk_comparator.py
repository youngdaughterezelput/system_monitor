from typing import List, Dict
from dataclasses import dataclass
from disk_health import DiskHealth, DiskHealthAnalyzer
from disk_info import DiskInfoCollector

@dataclass
class DiskComparison:
    disk1: str
    disk2: str
    parameters: Dict[str, tuple]

class DiskComparator:
    def __init__(self):
        self.info_collector = DiskInfoCollector()
        self.health_analyzer = DiskHealthAnalyzer()

    def compare_disks(self, disk1: str, disk2: str) -> DiskComparison:
        info1 = self.info_collector.get_partition_info(disk1)
        info2 = self.info_collector.get_partition_info(disk2)
        
        health1 = self.health_analyzer.get_health(disk1)
        health2 = self.health_analyzer.get_health(disk2)

        return DiskComparison(
            disk1=disk1,
            disk2=disk2,
            parameters={
                "total_size": (info1.total, info2.total),
                "used_space": (info1.used, info2.used),
                "temperature": (health1.temperature if health1 else None, 
                              health2.temperature if health2 else None),
                "bad_sectors": (health1.bad_sectors if health1 else 0,
                              health2.bad_sectors if health2 else 0),
                "lifespan": (health1.lifespan if health1 else None,
                           health2.lifespan if health2 else None)
            }
        )