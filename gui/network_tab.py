from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                            QTreeWidgetItem, QPushButton, QLineEdit, 
                            QTextEdit, QLabel, QHeaderView)
from PyQt5.QtCore import Qt
from network_diagnostics import NetworkDiagnostics

class NetworkTab(QWidget):
    def __init__(self):
        super().__init__()
        self.diagnostics = NetworkDiagnostics()
        self.init_ui()
    
    def init_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Connection monitoring
        self.connections_tree = QTreeWidget()
        self.connections_tree.setHeaderLabels(["Protocol", "Local Address", "Remote Address", "Status", "PID"])
        self.connections_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.layout.addWidget(QLabel("Active Connections:"))
        self.layout.addWidget(self.connections_tree)
        
        # Network tools
        self.layout.addWidget(QLabel("\nNetwork Tools:"))
        
        # Ping section
        ping_layout = QHBoxLayout()
        self.ping_input = QLineEdit()
        self.ping_input.setPlaceholderText("Enter host to ping")
        ping_button = QPushButton("Ping")
        ping_button.clicked.connect(self.run_ping)
        ping_layout.addWidget(self.ping_input)
        ping_layout.addWidget(ping_button)
        self.layout.addLayout(ping_layout)
        
        self.ping_output = QTextEdit()
        self.ping_output.setReadOnly(True)
        self.layout.addWidget(self.ping_output)
        
        # Traceroute section
        trace_layout = QHBoxLayout()
        self.trace_input = QLineEdit()
        self.trace_input.setPlaceholderText("Enter host for traceroute")
        trace_button = QPushButton("Traceroute")
        trace_button.clicked.connect(self.run_trace)
        trace_layout.addWidget(self.trace_input)
        trace_layout.addWidget(trace_button)
        self.layout.addLayout(trace_layout)
        
        self.trace_output = QTextEdit()
        self.trace_output.setReadOnly(True)
        self.layout.addWidget(self.trace_output)
        
        self.update_connections()
    
    def update_connections(self):
        """Update the active connections list"""
        self.connections_tree.clear()
        connections = self.diagnostics.get_connections()
        
        for conn in connections:
            item = QTreeWidgetItem(self.connections_tree)
            item.setText(0, f"{conn['family']}/{conn['type']}")
            item.setText(1, conn['local_addr'] or "")
            item.setText(2, conn['remote_addr'] or "")
            item.setText(3, conn['status'])
            item.setText(4, str(conn['pid']) if conn['pid'] else "")
    
    def run_ping(self):
        """Execute ping command"""
        host = self.ping_input.text().strip()
        if not host:
            return
            
        result = self.diagnostics.ping_host(host)
        output = result['output']
        
        if result['success']:
            stats = result['stats']
            output += f"\n\nStatistics:\n"
            output += f"Packet loss: {stats.get('packet_loss', 0)}%\n"
            output += f"RTT min/avg/max/mdev = {stats.get('rtt_min', 0):.3f}/"
            output += f"{stats.get('rtt_avg', 0):.3f}/"
            output += f"{stats.get('rtt_max', 0):.3f}/"
            output += f"{stats.get('rtt_mdev', 0):.3f} ms"
        
        self.ping_output.setPlainText(output)
    
    def run_trace(self):
        """Execute traceroute command"""
        host = self.trace_input.text().strip()
        if not host:
            return
            
        result = self.diagnostics.trace_route(host)
        self.trace_output.setPlainText(result['output'])