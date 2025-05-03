import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QMessageBox, QComboBox, QTableWidget,
    QTableWidgetItem, QLabel, QTabWidget, QHeaderView,
    QTreeWidget, QTreeWidgetItem, QSizePolicy, QStatusBar
)
from PyQt5.QtCore import Qt, QSize
import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from disk_analyzer import DiskAnalyzer
from disk_info import DiskInfoCollector

class DiskTab(QWidget):
    def __init__(self):
        super().__init__()
        self.info_collector = DiskInfoCollector()
        self.analyzer = DiskAnalyzer()
        self.status_bar = QStatusBar()
        self.canvas = None
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Vertical)
        
        # Верхняя панель: дерево и таблицы
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Панель управления
        control_widget = self.create_controls()
        top_layout.addWidget(control_widget)
        
        # Вкладки с информацией
        self.info_tabs = QTabWidget()
        self.info_tabs.addTab(self.create_tree_widget(), "Partitions")
        self.info_tabs.addTab(self.create_tables(), "Analysis Data")
        top_layout.addWidget(self.info_tabs)
        
        # Нижняя панель: графики
        self.graph_widget = QWidget()
        self.graph_layout = QVBoxLayout(self.graph_widget)
        self.graph_layout.setContentsMargins(0, 0, 0, 0)
        
        splitter.addWidget(top_widget)
        splitter.addWidget(self.graph_widget)
        splitter.setSizes([400, 600])  # 40% верх, 60% низ
        
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.status_bar)

        self.update_info()

    def create_controls(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.disk_selector = QComboBox()
        self.update_disk_list()
        
        self.analyze_btn = QPushButton("Analyze Disk")
        self.analyze_btn.clicked.connect(self.run_analysis)
        
        layout.addWidget(QLabel("Select Disk:"))
        layout.addWidget(self.disk_selector)
        layout.addWidget(self.analyze_btn)
        return widget

    def create_tree_widget(self):
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Parameter", "Value"])
        self.tree_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree_widget.header().setSectionResizeMode(1, QHeaderView.Stretch)
        return self.tree_widget

    def create_tables(self):
        tabs = QTabWidget()
        
        # Таблица общей статистики
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(2)
        self.summary_table.setHorizontalHeaderLabels(["Parameter", "Value"])
        tabs.addTab(self.summary_table, "Summary")
        
        # Таблица больших файлов
        self.large_files_table = QTableWidget()
        self.large_files_table.setColumnCount(2)
        self.large_files_table.setHorizontalHeaderLabels(["File Path", "Size (GB)"])
        tabs.addTab(self.large_files_table, "Large Files")
        
        # Таблица типов файлов
        self.file_types_table = QTableWidget()
        self.file_types_table.setColumnCount(2)
        self.file_types_table.setHorizontalHeaderLabels(["File Type", "Total Size (GB)"])
        tabs.addTab(self.file_types_table, "File Types")
        
        return tabs

    def run_analysis(self):
        mountpoint = self.disk_selector.currentData()  # Используем userData вместо text
        if not mountpoint:
            QMessageBox.warning(self, "Ошибка", "Не выбран диск для анализа")
            return

        try:
            analysis_data = self.analyzer.analyze_partition(mountpoint)
            self.update_tables(analysis_data)
            self.update_plots(analysis_data)
            self.show_recommendations(analysis_data)
            
        except RuntimeError as e:
            QMessageBox.critical(self, "Ошибка анализа", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Неизвестная ошибка", f"Произошла непредвиденная ошибка: {str(e)}")

    def update_tables(self, data):
        # Общая статистика
        self.fill_table(self.summary_table, [
            ("Total Space", self.format_size(data['usage']['total'])),
            ("Used Space", self.format_size(data['usage']['used'])),
            ("Free Space", self.format_size(data['usage']['free'])),
            ("Usage Percent", f"{data['usage']['percent']}%")
        ])
        
        # Большие файлы
        large_files = [(f[0], self.format_size(f[1])) for f in data['large_files'][:100]]
        self.fill_table(self.large_files_table, large_files)
        
        # Типы файлов
        file_types = [(k, self.format_size(v)) for k, v in data['file_types'][:100]]
        self.fill_table(self.file_types_table, file_types)

    def fill_table(self, table, data):
        table.setRowCount(len(data))
        for row, (col1, col2) in enumerate(data):
            table.setItem(row, 0, QTableWidgetItem(str(col1)))
            table.setItem(row, 1, QTableWidgetItem(str(col2)))
        table.resizeColumnsToContents()

    def update_plots(self, data):
        # Очистка предыдущих графиков
        for i in reversed(range(self.graph_layout.count())):
            self.graph_layout.itemAt(i).widget().deleteLater()
        
        # Создание фигуры
        fig = Figure(figsize=(10, 8), tight_layout=True)
        self.canvas = FigureCanvas(fig)
        
        # Настройка сетки графиков
        gs = fig.add_gridspec(2, 2)
        
        # График 1: Использование диска
        ax1 = fig.add_subplot(gs[0, 0])
        sizes = [data['usage']['used'], data['usage']['free']]
        labels = [f'Used ({data["usage"]["percent"]}%)', 'Free']
        ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Disk Usage')
        
        # График 2: Топ файлов
        ax2 = fig.add_subplot(gs[0, 1])
        large_files = data['large_files'][:10]
        paths = [os.path.basename(f[0]) for f in large_files]
        sizes = [f[1]/(1024**3) for f in large_files]
        ax2.barh(paths, sizes, color='skyblue')
        ax2.set_xlabel('Size (GB)')
        ax2.set_title('Top 10 Large Files')
        
        # График 3: Типы файлов
        ax3 = fig.add_subplot(gs[1, 0])
        file_types = data['file_types'][:10]
        labels = [t[0] for t in file_types]
        sizes = [t[1]/(1024**3) for t in file_types]
        ax3.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax3.set_title('File Type Distribution')
        
        # График 4: Директории
        ax4 = fig.add_subplot(gs[1, 1])
        dirs = data['dir_sizes'][:10]
        paths = [os.path.basename(d[0]) for d in dirs]
        sizes = [d[1]/(1024**3) for d in dirs]
        ax4.bar(paths, sizes, color='lightgreen')
        ax4.set_ylabel('Size (GB)')
        ax4.set_title('Top 10 Directories')
        plt.setp(ax4.get_xticklabels(), rotation=45, ha='right')
        
        self.graph_layout.addWidget(self.canvas)
        self.canvas.draw()

    def show_recommendations(self, data):
        recommendations = []
        usage = data['usage']
        
        if usage['percent'] > 90:
            recommendations.append("⚠️ Critical disk usage! Free up space immediately.")
        elif usage['percent'] > 75:
            recommendations.append("⚠️ Warning: Disk usage over 75%")
            
        if len(data['large_files']) > 0:
            recommendations.append(f"🔍 Found {len(data['large_files'])} large files (>100MB)")
        
        # Показываем сообщение в статус-баре
        if recommendations:
            self.status_bar.showMessage(" | ".join(recommendations), 5000)
        else:
            self.status_bar.showMessage("✅ Disk status: OK", 3000)


    def update_disk_list(self):
        """Обновление списка доступных дисков с фильтрацией"""
        self.disk_selector.clear()
        try:
            for part in psutil.disk_partitions():
                # Пропускаем специальные разделы
                if not part.fstype or part.device.startswith(('none', 'tmpfs')):
                    continue

                # Проверяем доступность
                try:
                    psutil.disk_usage(part.mountpoint)
                    display_name = f"{part.device} ({part.mountpoint})"
                    self.disk_selector.addItem(display_name, part.mountpoint)
                except Exception:
                    continue

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка обновления списка дисков: {str(e)}")

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

    @staticmethod
    def format_size(size_bytes):
        return f"{size_bytes / (1024**3):.2f}" if size_bytes else "0.00"