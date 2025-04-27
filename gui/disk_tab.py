from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, 
                            QTreeWidgetItem, QHeaderView)
from disk_info import DiskInfoCollector

class DiskTab(QWidget):
    def __init__(self):
        super().__init__()
        self.info_collector = DiskInfoCollector()
        self.init_ui()
    
    def init_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Parameter", "Value"])
        self.tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree_widget.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.layout.addWidget(self.tree_widget)
        
        self.update_info()
    
    def update_info(self):
        """Update the displayed disk information"""
        self.tree_widget.clear()
        info = self.info_collector.collect_all()
        
        # Add partitions information
        for partition in info['partitions']:
            part_item = QTreeWidgetItem(self.tree_widget)
            part_item.setText(0, f"Device: {partition['device']}")
            part_item.setText(1, f"Mountpoint: {partition['mountpoint']}")
            
            # Add partition details
            details = [
                ("Filesystem", partition['fstype']),
                ("Options", partition['opts'])
            ]
            
            if 'error' in partition:
                details.append(("Error", partition['error']))
            else:
                details.extend([
                    ("Total Size", f"{self.info_collector.bytes_to_gb(partition['total'])} GB"),
                    ("Used", f"{self.info_collector.bytes_to_gb(partition['used'])} GB ({partition['percent']}%)"),
                    ("Free", f"{self.info_collector.bytes_to_gb(partition['free'])} GB")
                ])
            
            for name, value in details:
                child = QTreeWidgetItem(part_item)
                child.setText(0, name)
                child.setText(1, str(value))
        
        # Add IO counters if available
        if info['io_counters']:
            io_item = QTreeWidgetItem(self.tree_widget)
            io_item.setText(0, "Disk I/O Counters")
            
            io_data = [
                ("Read Bytes", f"{self.info_collector.bytes_to_gb(info['io_counters']['read_bytes'])} GB"),
                ("Write Bytes", f"{self.info_collector.bytes_to_gb(info['io_counters']['write_bytes'])} GB"),
                ("Read Count", str(info['io_counters']['read_count'])),
                ("Write Count", str(info['io_counters']['write_count']))
            ]
            
            for name, value in io_data:
                child = QTreeWidgetItem(io_item)
                child.setText(0, name)
                child.setText(1, value)