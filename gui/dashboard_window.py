from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QTabWidget)
from PyQt5.QtCore import QTimer, Qt
from system_info import SystemInfoCollector
from disk_info import DiskInfoCollector
from network_diagnostics import NetworkDiagnostics

class DashboardWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Dashboard")
        self.setGeometry(200, 200, 800, 600)
        
        self.system_collector = SystemInfoCollector()
        self.disk_collector = DiskInfoCollector()
        self.network_diagnostics = NetworkDiagnostics()
        
        self.init_ui()
        self.start_updates()
    
    def init_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # System tab
        self.system_tab = QWidget()
        self.system_layout = QVBoxLayout()
        self.system_tab.setLayout(self.system_layout)
        
        self.cpu_label = QLabel("CPU:")
        self.system_layout.addWidget(self.cpu_label)
        
        self.mem_label = QLabel("Memory:")
        self.system_layout.addWidget(self.mem_label)
        
        # Disk tab
        self.disk_tab = QWidget()
        self.disk_layout = QVBoxLayout()
        self.disk_tab.setLayout(self.disk_layout)
        
        self.disk_text = QTextEdit()
        self.disk_text.setReadOnly(True)
        self.disk_layout.addWidget(self.disk_text)
        
        # Network tab
        self.network_tab = QWidget()
        self.network_layout = QVBoxLayout()
        self.network_tab.setLayout(self.network_layout)
        
        self.network_stats_text = QTextEdit()
        self.network_stats_text.setReadOnly(True)
        self.network_layout.addWidget(self.network_stats_text)
        
        # Add tabs
        self.tabs.addTab(self.system_tab, "System")
        self.tabs.addTab(self.disk_tab, "Disks")
        self.tabs.addTab(self.network_tab, "Network")
        
        # Refresh button
        refresh_btn = QPushButton("Manual Refresh")
        refresh_btn.clicked.connect(self.update_all)
        self.layout.addWidget(refresh_btn, alignment=Qt.AlignRight)
    
    def start_updates(self):
        """Start periodic updates"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all)
        self.timer.start(5000)  # Update every 5 seconds
        self.update_all()
    
    def update_all(self):
        """Update all dashboard information"""
        self.update_system_info()
        self.update_disk_info()
        self.update_network_info()
    
    def update_system_info(self):
        """Update system information"""
        cpu = self.system_collector.get_cpu_info()
        mem = self.system_collector.get_memory_info()
        
        cpu_text = (f"Physical cores: {cpu['physical_cores']}\n"
                   f"Logical cores: {cpu['logical_cores']}\n"
                   f"Current usage: {cpu['usage_percent']}%")
        
        mem_text = (f"Total: {self.system_collector.bytes_to_gb(mem['total'])} GB\n"
                   f"Used: {self.system_collector.bytes_to_gb(mem['used'])} GB ({mem['percent']}%)\n"
                   f"Available: {self.system_collector.bytes_to_gb(mem['available'])} GB")
        
        self.cpu_label.setText(f"CPU:\n{cpu_text}")
        self.mem_label.setText(f"Memory:\n{mem_text}")
    
    def update_disk_info(self):
        """Update disk information"""
        info = self.disk_collector.collect_all()
        text = []
        
        for partition in info['partitions']:
            text.append(f"Device: {partition['device']}")
            text.append(f"Mountpoint: {partition['mountpoint']}")
            if 'error' in partition:
                text.append(f"Error: {partition['error']}\n")
            else:
                text.append(f"Total: {self.disk_collector.bytes_to_gb(partition['total'])} GB")
                text.append(f"Used: {self.disk_collector.bytes_to_gb(partition['used'])} GB ({partition['percent']}%)")
                text.append(f"Free: {self.disk_collector.bytes_to_gb(partition['free'])} GB\n")
        
        self.disk_text.setPlainText("\n".join(text))
    
    def update_network_info(self):
        """Update network information"""
        stats = self.network_diagnostics.get_network_stats()
        text = [
            f"Bytes sent: {self.disk_collector.bytes_to_gb(stats['bytes_sent'])} GB",
            f"Bytes received: {self.disk_collector.bytes_to_gb(stats['bytes_recv'])} GB",
            f"Packets sent: {stats['packets_sent']}",
            f"Packets received: {stats['packets_recv']}",
            f"Errors in: {stats['errin']}",
            f"Errors out: {stats['errout']}",
            f"Dropped in: {stats['dropin']}",
            f"Dropped out: {stats['dropout']}"
        ]
        
        self.network_stats_text.setPlainText("\n".join(text))