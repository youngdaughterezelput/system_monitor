from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTextEdit
from PyQt5.QtCore import QTimer, Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from collections import deque
import psutil
import platform
import socket
from system_info import SystemInfoCollector

class SystemTab(QWidget):
    def __init__(self):
        super().__init__()
        self.info_collector = SystemInfoCollector()
        # Очереди для хранения истории значений
        self.cpu_history = deque(maxlen=60)
        self.mem_history = deque(maxlen=60)
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Вертикальный разделитель
        splitter = QSplitter(Qt.Vertical)
        
        # Верхняя часть - текстовая информация
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        splitter.addWidget(self.info_text)
        
        # Нижняя часть - графики
        graph_widget = QWidget()
        graph_layout = QHBoxLayout(graph_widget)
        
        # График CPU
        self.cpu_fig = Figure(figsize=(6, 3))
        self.cpu_canvas = FigureCanvas(self.cpu_fig)
        self.cpu_ax = self.cpu_fig.add_subplot(111)
        self.cpu_ax.set_title('Использование CPU (%)')
        self.cpu_ax.set_ylim(0, 100)
        self.cpu_ax.set_xlim(0, 60)
        self.cpu_ax.grid(True)
        self.cpu_line, = self.cpu_ax.plot([], [], 'b-')
        graph_layout.addWidget(self.cpu_canvas)
        
        # График памяти
        self.mem_fig = Figure(figsize=(6, 3))
        self.mem_canvas = FigureCanvas(self.mem_fig)
        self.mem_ax = self.mem_fig.add_subplot(111)
        self.mem_ax.set_title('Использование памяти (%)')
        self.mem_ax.set_ylim(0, 100)
        self.mem_ax.set_xlim(0, 60)
        self.mem_ax.grid(True)
        self.mem_line, = self.mem_ax.plot([], [], 'r-')
        graph_layout.addWidget(self.mem_canvas)
        
        splitter.addWidget(graph_widget)
        splitter.setSizes([300, 200])
        
        main_layout.addWidget(splitter)
        
        # Настройка таймера для обновления данных
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_info)
        self.timer.start(1000)  # Обновление каждую секунду
        
        # Первоначальное обновление
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
        """Обновление информации и графиков"""
        # Сбор данных
        info = self.info_collector.collect_all()
        cpu_percent = info['cpu']['usage_percent']
        mem_percent = info['memory']['percent']
        
        # Обновление истории
        self.cpu_history.append(cpu_percent)
        self.mem_history.append(mem_percent)
        
        # Обновление текстовой информации
        self.info_text.setPlainText(self.format_info(info))
        
        # Обновление графиков
        self.update_cpu_plot()
        self.update_mem_plot()

    def update_cpu_plot(self):
        """Обновление графика использования CPU"""
        if self.cpu_history:
            self.cpu_ax.set_title(f'Использование CPU: {self.cpu_history[-1]}%')
            self.cpu_line.set_data(range(len(self.cpu_history)), list(self.cpu_history))
            self.cpu_ax.set_xlim(0, max(10, len(self.cpu_history)))
            self.cpu_canvas.draw()

    def update_mem_plot(self):
        """Обновление графика использования памяти"""
        if self.mem_history:
            self.mem_ax.set_title(f'Использование памяти: {self.mem_history[-1]}%')
            self.mem_line.set_data(range(len(self.mem_history)), list(self.mem_history))
            self.mem_ax.set_xlim(0, max(10, len(self.mem_history)))
            self.mem_canvas.draw()