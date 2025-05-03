import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QMessageBox, QComboBox, QTableWidget,
    QTableWidgetItem, QLabel, QTabWidget, QHeaderView,
    QTreeWidget, QTreeWidgetItem, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer
import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from disk_analyzer import DiskAnalyzer
from disk_info import DiskInfoCollector
from disk_health import DiskHealthAnalyzer, DiskHealth
from disk_comparator import DiskComparator

class DiskTab(QWidget):
    def __init__(self):
        super().__init__()
        self.info_collector = DiskInfoCollector()
        self.analyzer = DiskAnalyzer()
        self.health_analyzer = DiskHealthAnalyzer()
        self.comparator = DiskComparator()
        self.canvas = None
        self.tabs = QTabWidget()
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        self.init_main_tab()
        self.init_health_tab()
        self.init_comparison_tab()
        
        main_layout.addWidget(self.tabs)
        self.update_disk_list()
        self.update_info()

    def init_main_tab(self):
        main_tab = QWidget()
        layout = QVBoxLayout(main_tab)
        
        splitter = QSplitter(Qt.Vertical)
        
        # Top panel
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.addWidget(self.create_tree_widget())
        top_layout.addWidget(self.create_controls())
        
        # Bottom panel
        self.graph_widget = QWidget()
        self.graph_layout = QVBoxLayout(self.graph_widget)
        
        splitter.addWidget(top_widget)
        splitter.addWidget(self.graph_widget)
        splitter.setSizes([300, 400])
        
        layout.addWidget(splitter)
        self.tabs.addTab(main_tab, "Основная")

    def init_health_tab(self):
        health_tab = QWidget()
        layout = QVBoxLayout(health_tab)
        
        self.health_table = QTableWidget()
        self.health_table.setColumnCount(3)
        self.health_table.setHorizontalHeaderLabels(["Параметр", "Значение", "Статус"])
        self.health_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.health_table)
        self.tabs.addTab(health_tab, "Здоровье диска")

    def init_comparison_tab(self):
        compare_tab = QWidget()
        layout = QVBoxLayout(compare_tab)
        
        self.compare_selector1 = QComboBox()
        self.compare_selector2 = QComboBox()
        self.update_compare_selectors()
        
        compare_btn = QPushButton("Сравнить диски")
        compare_btn.clicked.connect(self.compare_disks)
        
        self.compare_result = QTextEdit()
        self.compare_result.setReadOnly(True)
        
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Диск 1:"))
        selector_layout.addWidget(self.compare_selector1)
        selector_layout.addWidget(QLabel("Диск 2:"))
        selector_layout.addWidget(self.compare_selector2)
        selector_layout.addWidget(compare_btn)
        
        layout.addLayout(selector_layout)
        layout.addWidget(self.compare_result)
        self.tabs.addTab(compare_tab, "Сравнение")

    def create_tree_widget(self):
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Параметр", "Значение"])
        self.tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree_widget.header().setSectionResizeMode(1, QHeaderView.Stretch)
        return self.tree_widget
    
    def update_info(self):
        self.tree_widget.clear()
        info = self.info_collector.collect_all()
        
        for part in info['partitions']:
            item = QTreeWidgetItem(self.tree_widget)
            item.setText(0, part['device'])
            item.setText(1, part['mountpoint'])
            
            details = [
                ("Filesystem", part['fstype']),
                ("Options", part['opts']),
                ("Total", self.format_size(part['total'])),
                ("Used", self.format_size(part['used'])),
                ("Free", self.format_size(part['free'])),
                ("Usage", f"{part['percent']}%")
            ]
            
            for name, value in details:
                child = QTreeWidgetItem(item)
                child.setText(0, name)
                child.setText(1, value)

    def create_controls(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.disk_selector = QComboBox()
        self.update_disk_list()
        
        self.analyze_btn = QPushButton("Анализировать диск")
        self.analyze_btn.clicked.connect(self.run_analysis)
        
        layout.addWidget(QLabel("Выберите диск:"))
        layout.addWidget(self.disk_selector)
        layout.addWidget(self.analyze_btn)
        return widget

    def update_disk_list(self):
        self.disk_selector.clear()
        for part in psutil.disk_partitions():
            if part.fstype and part.device:
                self.disk_selector.addItem(
                    f"{part.device} ({part.mountpoint})",
                    part.mountpoint
                )

    def update_compare_selectors(self):
        self.compare_selector1.clear()
        self.compare_selector2.clear()
        for part in psutil.disk_partitions():
            if part.fstype and part.device:
                text = f"{part.device} ({part.mountpoint})"
                self.compare_selector1.addItem(text, part.mountpoint)
                self.compare_selector2.addItem(text, part.mountpoint)

    def run_analysis(self):
        mountpoint = self.disk_selector.currentData()
        if not mountpoint:
            QMessageBox.warning(self, "Ошибка", "Выберите диск для анализа")
            return
        
        try:
            analysis_data = self.analyzer.analyze_partition(mountpoint)
            self.update_tables(analysis_data)
            self.update_plots(analysis_data)
            self.show_health_info(mountpoint)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка анализа", str(e))

    def update_tables(self, data):
        # Summary table
        self.fill_table([
            ("Всего места", self.format_size(data['usage']['total'])),
            ("Использовано", self.format_size(data['usage']['used'])),
            ("Свободно", self.format_size(data['usage']['free'])),
            ("Заполнено", f"{data['usage']['percent']}%")
        ])

    def fill_table(self, data):
        pass  # Реализация заполнения таблиц

    def update_plots(self, data):
        for i in reversed(range(self.graph_layout.count())):
            self.graph_layout.itemAt(i).widget().deleteLater()
        
        fig = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(fig)
        
        # Disk Usage
        ax1 = fig.add_subplot(221)
        sizes = [data['usage']['used'], data['usage']['free']]
        labels = [f'Used ({data["usage"]["percent"]}%)', 'Free']
        ax1.pie(sizes, labels=labels, autopct='%1.1f%%')
        
        # Large Files
        ax2 = fig.add_subplot(222)
        large_files = data['large_files'][:10]
        paths = [os.path.basename(f[0]) for f in large_files]
        sizes = [f[1]/(1024**3) for f in large_files]
        ax2.barh(paths, sizes)
        
        self.graph_layout.addWidget(self.canvas)
        self.canvas.draw()

    def show_health_info(self, device: str):
        health = self.health_analyzer.get_health(device)
        if not health:
            QMessageBox.warning(self, "Ошибка", "Данные S.M.A.R.T. недоступны")
            return
        
        self.health_table.setRowCount(len(health.attributes))
        for row, (name, attr) in enumerate(health.attributes.items()):
            status = "✔️" if attr.value > attr.threshold else "⚠️" if attr.value == attr.threshold else "❌"
            self.health_table.setItem(row, 0, QTableWidgetItem(name))
            self.health_table.setItem(row, 1, QTableWidgetItem(str(attr.value)))
            self.health_table.setItem(row, 2, QTableWidgetItem(status))

    def compare_disks(self):
        disk1 = self.compare_selector1.currentData()
        disk2 = self.compare_selector2.currentData()
        
        if not disk1 or not disk2:
            QMessageBox.warning(self, "Ошибка", "Выберите два диска для сравнения")
            return
        
        try:
            comparison = self.comparator.compare_disks(disk1, disk2)
            report = self.generate_comparison_report(comparison)
            self.compare_result.setPlainText(report)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сравнения", str(e))

    def generate_comparison_report(self, comparison):
        report = f"""
        Отчет сравнения дисков:
        ========================
        Диск 1: {comparison.disk1}
        Диск 2: {comparison.disk2}

        Параметры:
        ----------
        Общий размер: {self.format_size(comparison.parameters['total_size'][0])} vs {self.format_size(comparison.parameters['total_size'][1])}
        Использовано: {self.format_size(comparison.parameters['used_space'][0])} vs {self.format_size(comparison.parameters['used_space'][1])}
        Температура: {comparison.parameters['temperature'][0] or 'N/A'}°C vs {comparison.parameters['temperature'][1] or 'N/A'}°C
        Битые сектора: {comparison.parameters['bad_sectors'][0]} vs {comparison.parameters['bad_sectors'][1]}
        Срок службы: {comparison.parameters['lifespan'][0] or 'N/A'}% vs {comparison.parameters['lifespan'][1] or 'N/A'}%
        """
        return report

    @staticmethod
    def format_size(size_bytes):
        return f"{size_bytes / (1024**3):.2f} GB" if size_bytes else "0.00 GB"