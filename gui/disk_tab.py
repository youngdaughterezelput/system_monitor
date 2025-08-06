import os
import platform
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QMessageBox, QComboBox, QTableWidget,
    QTableWidgetItem, QLabel, QTabWidget, QHeaderView,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
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
        self.current_disk = None
        self.health_timer = QTimer()
        self.health_timer.timeout.connect(self.update_health_info)
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
        
        # Индикатор общего состояния
        self.health_status_bar = QProgressBar()
        self.health_status_bar.setRange(0, 100)
        self.health_status_bar.setTextVisible(True)
        self.health_status_bar.setFormat("Состояние диска: %p%")
        layout.addWidget(self.health_status_bar)
        
        # Таблица с атрибутами SMART
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
        
        # Кнопка для постоянного мониторинга здоровья
        self.monitor_btn = QPushButton("Мониторить здоровье")
        self.monitor_btn.setCheckable(True)
        self.monitor_btn.toggled.connect(self.toggle_health_monitoring)
        
        layout.addWidget(QLabel("Выберите диск:"))
        layout.addWidget(self.disk_selector)
        layout.addWidget(self.analyze_btn)
        layout.addWidget(self.monitor_btn)
        return widget
    
    def toggle_health_monitoring(self, checked):
        if checked:
            self.monitor_btn.setText("Остановить мониторинг")
            self.health_timer.start(5000)  # Обновление каждые 5 секунд
        else:
            self.monitor_btn.setText("Мониторить здоровье")
            self.health_timer.stop()

    def update_health_info(self):
        if self.current_disk:
            self.show_health_info(self.current_disk)

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
                # Сохраняем кортеж (устройство, точка монтирования)
                self.compare_selector1.addItem(text, (part.device, part.mountpoint))
                self.compare_selector2.addItem(text, (part.device, part.mountpoint))

    def run_analysis(self):
        try:
            mountpoint = self.disk_selector.currentData()
            if not mountpoint:
                raise ValueError("No disk selected")

            # Проверка существования точки монтирования
            if not os.path.exists(mountpoint):
                raise FileNotFoundError(f"Mount point {mountpoint} does not exist")

            self.current_disk = mountpoint
            analysis_data = self.analyzer.analyze_partition(mountpoint)
            self.update_tables(analysis_data)
            self.update_plots(analysis_data)
            self.show_health_info(mountpoint)
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

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
        try:
            health = self.health_analyzer.get_health(device)
            if health is None:
                QMessageBox.warning(
                    self, 
                    "Ошибка здоровья диска", 
                    "Не удалось получить данные о здоровье диска. "
                    "Убедитесь, что smartmontools установлены и доступны в PATH."
                )
                return
            
            # Обновляем индикатор здоровья
            health_value = health.lifespan or 100
            if health.health_status == "PASSED":
                health_value = 100
            elif health.health_status == "FAILED":
                health_value = 0
                
            self.health_status_bar.setValue(int(health_value))
            
            # Форматируем статус в зависимости от значения
            if health_value > 80:
                self.health_status_bar.setStyleSheet("QProgressBar::chunk { background-color: green; }")
            elif health_value > 40:
                self.health_status_bar.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
            else:
                self.health_status_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
            
            # Заполняем таблицу атрибутов
            self.health_table.setRowCount(len(health.attributes))
            for row, (name, attr) in enumerate(health.attributes.items()):
                # Определяем статус атрибута
                if attr.value > attr.threshold:
                    status = "✔️"
                    color = "green"
                elif attr.value == attr.threshold:
                    status = "⚠️"
                    color = "orange"
                else:
                    status = "❌"
                    color = "red"
                
                self.health_table.setItem(row, 0, QTableWidgetItem(name))
                self.health_table.setItem(row, 1, QTableWidgetItem(str(attr.value)))
                
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QColor(color))
                self.health_table.setItem(row, 2, status_item)

        except Exception as e:
            QMessageBox.warning(self, "Ошибка здоровья диска", str(e))

    def get_device_by_mountpoint(self, mountpoint: str) -> str:
        """Получает имя устройства по точке монтирования"""
        for part in psutil.disk_partitions():
            if part.mountpoint == mountpoint:
                return part.device
        return mountpoint  # fallback

    def compare_disks(self):
        # Получаем кортеж (device, mountpoint)
        disk_data1 = self.compare_selector1.currentData()
        disk_data2 = self.compare_selector2.currentData()
        
        if not disk_data1 or not disk_data2:
            QMessageBox.warning(self, "Ошибка", "Выберите два диска для сравнения")
            return
        
        try:
            # Извлекаем имя устройства из кортежа
            device1 = disk_data1[0] if isinstance(disk_data1, tuple) else disk_data1
            device2 = disk_data2[0] if isinstance(disk_data2, tuple) else disk_data2
            
            comparison = self.comparator.compare_disks(device1, device2)
            report = self.generate_comparison_report(comparison)
            self.compare_result.setPlainText(report)
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Ошибка сравнения", 
                f"Произошла ошибка при сравнении дисков:\n{str(e)}"
            )

    def generate_comparison_report(self, comparison):
        # Проверка наличия необходимых данных
        def safe_get(data, key, default="N/A"):
            return data.get(key, [default, default])
        
        # Форматирование значений
        def format_value(value):
            if value is None: 
                return "N/A"
            if isinstance(value, (int, float)):
                return f"{value:.2f}" if value > 100 else f"{value}"
            return str(value)
        
        # Получение параметров с проверкой
        params = comparison.parameters if hasattr(comparison, 'parameters') else {}
        
        # Извлечение данных с защитой от ошибок
        total_size = safe_get(params, 'total_size', [0, 0])
        used_space = safe_get(params, 'used_space', [0, 0])
        temperature = safe_get(params, 'temperature', [None, None])
        bad_sectors = safe_get(params, 'bad_sectors', [0, 0])
        lifespan = safe_get(params, 'lifespan', [None, None])
        
        report = f"""
        Отчет сравнения дисков:
        ========================
        Диск 1: {comparison.disk1}
        Диск 2: {comparison.disk2}

        Параметры:
        ----------
        Общий размер: {self.format_size(total_size[0])} vs {self.format_size(total_size[1])}
        Использовано: {self.format_size(used_space[0])} vs {self.format_size(used_space[1])}
        Температура: {format_value(temperature[0])}°C vs {format_value(temperature[1])}°C
        Битые сектора: {format_value(bad_sectors[0])} vs {format_value(bad_sectors[1])}
        Срок службы: {format_value(lifespan[0])}% vs {format_value(lifespan[1])}%
        """
        return report

    @staticmethod
    def format_size(size_bytes):
        if not isinstance(size_bytes, (int, float)):
            return "N/A"
        return f"{size_bytes / (1024**3):.2f} GB" if size_bytes else "0.00 GB"