import psutil
from typing import List, Dict, Optional

class DiskInfoCollector:
    @staticmethod
    def bytes_to_gb(bytes_value: int) -> float:
        """Convert bytes to gigabytes"""
        return round(bytes_value / (1024 ** 3), 2)
    
    @staticmethod
    def get_partitions() -> List[Dict]:
        """Get disk partitions information"""
        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'opts': partition.opts,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except:
                partitions.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'opts': partition.opts,
                    'error': "Unable to get usage info"
                })
        return partitions
    
    def get_partition_info(self, mountpoint: str) -> dict:
        """Получение информации о конкретном разделе"""
        for part in self.get_partitions():
            if part['mountpoint'] == mountpoint:
                return part
        raise ValueError(f"Partition {mountpoint} not found")
    
    @staticmethod
    def get_io_counters() -> Optional[Dict]:
        """Get disk I/O counters"""
        try:
            io = psutil.disk_io_counters()
            return {
                'read_bytes': io.read_bytes,
                'write_bytes': io.write_bytes,
                'read_count': io.read_count,
                'write_count': io.write_count
            } if io else None
        except:
            return None
    
    def collect_all(self) -> Dict:
        """Collect all disk information"""
        return {
            'partitions': self.get_partitions(),
            'io_counters': self.get_io_counters()
        }