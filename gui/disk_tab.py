from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QFileDialog, QMessageBox, QComboBox, QTableWidget,
                            QTableWidgetItem, QLabel, QTabWidget, QHeaderView, 
                            QTreeWidget, QTreeWidgetItem)
import psutil
from disk_info import DiskInfoCollector
from disk_analyzer import DiskAnalyzer

class DiskTab(QWidget):
    def __init__(self):
        super().__init__()
        self.info_collector = DiskInfoCollector()
        self.analyzer = DiskAnalyzer()
        self.canvas = None  # Инициализация атрибута
        self.init_ui()
    
    def init_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Дерево информации о дисках
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Parameter", "Value"])
        self.tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree_widget.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.layout.addWidget(self.tree_widget)

        # Элементы анализа
        self.analysis_layout = QVBoxLayout()
        
        # Выбор диска
        self.disk_selector = QComboBox()
        self.update_disk_list()
        
        # Кнопка анализа
        self.analyze_btn = QPushButton("Анализировать диск")
        self.analyze_btn.clicked.connect(self.run_analysis)
        
        # Вкладки с таблицами
        self.tabs = QTabWidget()
        self.init_tables()
        
        # Рекомендации
        self.recommendations_label = QLabel()
        self.recommendations_label.setWordWrap(True)
        self.recommendations_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        
        # Компоновка элементов
        self.layout.addWidget(QLabel("Выберите диск для анализа:"))
        self.layout.addWidget(self.disk_selector)
        self.layout.addWidget(self.analyze_btn)
        self.layout.addWidget(self.tabs)
        self.layout.addWidget(self.recommendations_label)
        
        self.update_info()

    def init_tables(self):
        # Таблица с общей информацией
        self.summary_table = self.create_table(
            ["Параметр", "Значение"], 
            QHeaderView.Stretch
        )
        
        # Таблица с большими файлами
        self.large_files_table = self.create_table(
            ["Файл", "Размер (GB)"], 
            QHeaderView.Stretch
        )
        
        # Таблица с типами файлов
        self.file_types_table = self.create_table(
            ["Тип файла", "Общий размер (GB)"], 
            QHeaderView.Stretch
        )
        
        # Добавление вкладок
        self.tabs.addTab(self.create_tab(self.summary_table, "Общая статистика"), "Общая")
        self.tabs.addTab(self.create_tab(self.large_files_table, "Крупные файлы (>100MB)"), "Крупные файлы")
        self.tabs.addTab(self.create_tab(self.file_types_table, "Распределение по типам файлов"), "Типы файлов")

    def create_table(self, headers, resize_mode):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, resize_mode)
        return table

    def create_tab(self, table, title):
        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel(title))
        layout.addWidget(table)
        container.setLayout(layout)
        return container

    def update_disk_list(self):
        self.disk_selector.clear()
        for part in psutil.disk_partitions():
            self.disk_selector.addItem(part.mountpoint, part.device)
    
    def update_info(self):
        self.tree_widget.clear()
        info = self.info_collector.collect_all()
        
        # Информация о разделах
        for partition in info['partitions']:
            part_item = QTreeWidgetItem(self.tree_widget)
            part_item.setText(0, f"Устройство: {partition['device']}")
            part_item.setText(1, f"Точка монтирования: {partition['mountpoint']}")
            
            details = [
                ("Файловая система", partition['fstype']),
                ("Опции", partition['opts'])
            ]
            
            if 'error' in partition:
                details.append(("Ошибка", partition['error']))
            else:
                details.extend([
                    ("Общий размер", f"{self.format_size(partition['total'])} GB"),
                    ("Использовано", f"{self.format_size(partition['used'])} GB ({partition['percent']}%)"),
                    ("Свободно", f"{self.format_size(partition['free'])} GB")
                ])
            
            for name, value in details:
                child = QTreeWidgetItem(part_item)
                child.setText(0, name)
                child.setText(1, str(value))
        
        # Информация о вводе-выводе
        if info['io_counters']:
            io_item = QTreeWidgetItem(self.tree_widget)
            io_item.setText(0, "Операции ввода-вывода")
            io_data = [
                ("Прочитано", f"{self.format_size(info['io_counters']['read_bytes'])} GB"),
                ("Записано", f"{self.format_size(info['io_counters']['write_bytes'])} GB"),
                ("Операций чтения", str(info['io_counters']['read_count'])),
                ("Операций записи", str(info['io_counters']['write_count']))
            ]
            for name, value in io_data:
                child = QTreeWidgetItem(io_item)
                child.setText(0, name)
                child.setText(1, value)

    def run_analysis(self):
        mountpoint = self.disk_selector.currentText()
        try:
            # Удаление предыдущего canvas
            if self.canvas:
                self.layout().removeWidget(self.canvas)
                self.canvas.deleteLater()
                self.canvas = None

            # Анализ данных
            analysis_data = self.analyzer.analyze_partition(mountpoint)
            
            # Обновление таблиц
            self.update_summary_table(analysis_data['usage'])
            self.update_large_files_table(analysis_data['large_files'])
            self.update_file_types_table(analysis_data['file_types'])
            
            # Показать рекомендации
            self.show_recommendations(analysis_data['usage'], analysis_data)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def update_summary_table(self, usage):
        self.fill_table(self.summary_table, [
            ("Всего места", self.format_size(usage['total'])),
            ("Использовано", self.format_size(usage['used'])),
            ("Свободно", self.format_size(usage['free'])),
            ("Заполнено", f"{usage['percent']}%")
        ])

    def update_large_files_table(self, files):
        data = [(path, self.format_size(size)) for path, size in files]
        self.fill_table(self.large_files_table, data)

    def update_file_types_table(self, file_types):
        data = [(ext, self.format_size(size)) for ext, size in file_types]
        self.fill_table(self.file_types_table, data)

    def fill_table(self, table, data):
        table.setRowCount(len(data))
        for row, items in enumerate(data):
            for col, value in enumerate(items):
                table.setItem(row, col, QTableWidgetItem(str(value)))

    def show_recommendations(self, usage, analysis):
        recommendations = []
        
        if usage['percent'] > 90:
            recommendations.append("⚠️ Критическое заполнение диска! Срочно освободите место.")
        elif usage['percent'] > 75:
            recommendations.append("⚠️ Диск заполнен более чем на 75%. Рекомендуется очистка.")
        
        if len(analysis['large_files']) > 0:
            recommendations.append(f"🔍 Обнаружено {len(analysis['large_files'])} крупных файлов (>100MB)")
        
        self.recommendations_label.setText("\n".join(recommendations) if recommendations else 
            "✅ Проблемы не обнаружены. Диск в норме.")

    @staticmethod
    def format_size(size_bytes):
        return f"{size_bytes / (1024**3):.2f} GB"