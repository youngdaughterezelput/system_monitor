from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from system_core.system_info import SystemInfoCollector

class SystemTab(QWidget):
    def __init__(self):
        super().__init__()
        self.info_collector = SystemInfoCollector()
        self.init_ui()
    
    def init_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.layout.addWidget(self.info_text)
        
        self.update_info()
    
    def format_info(self, info: dict) -> str:
        """Format system information for display"""
        text = []
        
        # OS Info
        os_info = info['os']
        text.append("=== Operating System ===")
        text.append(f"System: {os_info['system']} {os_info['release']}")
        text.append(f"Version: {os_info['version']}")
        text.append(f"Architecture: {os_info['machine']}")
        text.append(f"Processor: {os_info['processor']}")
        text.append(f"Hostname: {os_info['hostname']}")
        
        # CPU Info
        cpu_info = info['cpu']
        text.append("\n=== CPU ===")
        text.append(f"Physical cores: {cpu_info['physical_cores']}")
        text.append(f"Logical cores: {cpu_info['logical_cores']}")
        text.append(f"Current usage: {cpu_info['usage_percent']}%")
        
        # Memory Info
        mem_info = info['memory']
        text.append("\n=== Memory ===")
        text.append(f"Total: {self.info_collector.bytes_to_gb(mem_info['total'])} GB")
        text.append(f"Available: {self.info_collector.bytes_to_gb(mem_info['available'])} GB")
        text.append(f"Used: {self.info_collector.bytes_to_gb(mem_info['used'])} GB ({mem_info['percent']}%)")
        
        # Network Info
        net_info = info['network']
        text.append("\n=== Network ===")
        for interface, data in net_info.items():
            text.append(f"\nInterface: {interface}")
            for ip in data['ipv4']:
                text.append(f"  IPv4: {ip}")
            for ip in data['ipv6']:
                text.append(f"  IPv6: {ip}")
            for mask in data['netmask']:
                text.append(f"  Netmask: {mask}")
        
        return "\n".join(text)
    
    def update_info(self):
        """Update the displayed system information"""
        info = self.info_collector.collect_all()
        self.info_text.setPlainText(self.format_info(info))