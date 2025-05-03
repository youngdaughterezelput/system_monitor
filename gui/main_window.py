from PyQt5.QtWidgets import QMainWindow, QTabWidget, QAction, QMenuBar
from system_tab import SystemTab
from disk_tab import DiskTab
from network_tab import NetworkTab
from dashboard_window import DashboardWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Monitor")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()
        self.init_menu()
    
    def init_ui(self):
        # Create tabs
        self.tabs = QTabWidget()
        
        # Add tabs
        self.system_tab = SystemTab()
        self.tabs.addTab(self.system_tab, "System Information")
        
        self.disk_tab = DiskTab()
        self.tabs.addTab(self.disk_tab, "Disk Information")
        
        self.network_tab = NetworkTab()
        self.tabs.addTab(self.network_tab, "Network Diagnostics")
        
        # Set central widget
        self.setCentralWidget(self.tabs)
    
    def init_menu(self):
        # Create menu bar
        menubar = self.menuBar()

        file_minu = menubar.addMenu("File")
        
        # Add view menu
        view_menu = menubar.addMenu("View")
        
        # Add dashboard action
        dashboard_action = QAction("Open Dashboard", self)
        dashboard_action.triggered.connect(self.open_dashboard)
        view_menu.addAction(dashboard_action)


        file_action = QAction("Exit", self)
        file_action.triggered.connect(self.exit_out)
        file_minu.addAction(file_action)
    
    def open_dashboard(self):
        """Open the dashboard window"""
        self.dashboard = DashboardWindow()
        self.dashboard.show()


    def exit_out(self):
        self.close()