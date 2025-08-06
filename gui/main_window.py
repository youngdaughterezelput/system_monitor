import platform
import ctypes
import sys
from PyQt5.QtWidgets import QMainWindow, QTabWidget, QAction, QMenuBar, QMessageBox
from system_tab import SystemTab
from disk_tab import DiskTab
from network_tab import NetworkTab
from disk_defrag import DefragTab

class MainWindow(QMainWindow):
    def __init__(self):
        # Проверяем, запущен ли в режиме отладки
        is_debug = hasattr(sys, 'gettrace') and sys.gettrace() is not None
        skip_admin = '--no-admin' in sys.argv  # Проверка флага пропуска прав
        
        # Проверка прав администратора (для Windows) только если не в режиме отладки
        if (platform.system() == "Windows" and 
            not is_debug and 
            not skip_admin and 
            not self.is_admin()):
            
            QMessageBox.critical(None, "Ошибка прав", 
                               "Программа требует прав администратора для работы с дефрагментацией.")
            sys.exit(1)
            
        super().__init__()
        self.setWindowTitle("System Monitor")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()
        self.init_menu()
    
    @staticmethod
    def is_admin():
        """Проверка прав администратора в Windows"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
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
        
        self.defrag_tab = DefragTab()  # Добавляем таб дефрагментации
        self.tabs.addTab(self.defrag_tab, "Defragmentation")
        
        # Set central widget
        self.setCentralWidget(self.tabs)
    
    def init_menu(self):
        # Create menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_action = QAction("Exit", self)
        file_action.triggered.connect(self.close)
        file_menu.addAction(file_action)


    def exit_out(self):
        self.close()