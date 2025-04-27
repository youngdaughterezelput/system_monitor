import platform
import psutil
import socket

class SystemInfoCollector:
    @staticmethod
    def bytes_to_gb(bytes_value: int) -> float:
        """Convert bytes to gigabytes"""
        return round(bytes_value / (1024 ** 3), 2)
    
    @staticmethod
    def get_os_info() -> dict:
        """Get operating system information"""
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'hostname': socket.gethostname()
        }
    
    @staticmethod
    def get_cpu_info() -> dict:
        """Get CPU information"""
        return {
            'physical_cores': psutil.cpu_count(logical=False),
            'logical_cores': psutil.cpu_count(logical=True),
            'usage_percent': psutil.cpu_percent()
        }
    
    @staticmethod
    def get_memory_info() -> dict:
        """Get memory information"""
        mem = psutil.virtual_memory()
        return {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'percent': mem.percent
        }
    
    @staticmethod
    def get_network_info() -> dict:
        """Get network information"""
        addrs = psutil.net_if_addrs()
        network_info = {}
        
        for interface, addresses in addrs.items():
            network_info[interface] = {
                'ipv4': [],
                'ipv6': [],
                'netmask': []
            }
            for addr in addresses:
                if addr.family == socket.AF_INET:
                    network_info[interface]['ipv4'].append(addr.address)
                    network_info[interface]['netmask'].append(addr.netmask)
                elif addr.family == socket.AF_INET6:
                    network_info[interface]['ipv6'].append(addr.address)
        
        return network_info
    
    def collect_all(self) -> dict:
        """Collect all system information"""
        return {
            'os': self.get_os_info(),
            'cpu': self.get_cpu_info(),
            'memory': self.get_memory_info(),
            'network': self.get_network_info()
        }