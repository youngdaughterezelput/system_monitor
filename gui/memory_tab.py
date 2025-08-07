import psutil
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QHeaderView, QSplitter, QComboBox,
    QMessageBox, QInputDialog, QDialog, QFormLayout, QLineEdit
)
from PyQt5.QtCore import Qt, QTimer
import requests
from datetime import datetime


class TelegramSettingsDialog(QDialog):
    """Диалоговое окно для настройки Telegram уведомлений"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки Telegram")
        self.setFixedSize(400, 200)

        layout = QFormLayout()

        self.bot_token_edit = QLineEdit()
        self.bot_token_edit.setPlaceholderText("123456789:AAF...")
        layout.addRow("Токен бота:", self.bot_token_edit)

        self.chat_id_edit = QLineEdit()
        self.chat_id_edit.setPlaceholderText("@channelname или 123456789")
        layout.addRow("ID чата/канала:", self.chat_id_edit)

        self.threshold_edit = QLineEdit()
        self.threshold_edit.setPlaceholderText("500")
        layout.addRow("Порог памяти (МБ):", self.threshold_edit)

        self.interval_edit = QLineEdit()
        self.interval_edit.setPlaceholderText("30")
        layout.addRow("Интервал сканирования (сек):", self.interval_edit)

        # Кнопки
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addRow(btn_layout)
        self.setLayout(layout)

    def get_settings(self):
        return {
            'bot_token': self.bot_token_edit.text().strip(),
            'chat_id': self.chat_id_edit.text().strip(),
            'threshold': int(self.threshold_edit.text()) if self.threshold_edit.text().strip() else 500,
            'interval': int(self.interval_edit.text()) if self.interval_edit.text().strip() else 30
        }

    def set_settings(self, settings):
        self.bot_token_edit.setText(settings.get('bot_token', ''))
        self.chat_id_edit.setText(settings.get('chat_id', ''))
        self.threshold_edit.setText(str(settings.get('threshold', 500)))
        self.interval_edit.setText(str(settings.get('interval', 30)))


class MemoryTab(QWidget):
    def __init__(self):
        super().__init__()
        self.is_monitoring = False
        self.monitor_thread = None
        self.history = {}  # {pid: [(time, mem_mb), ...]}
        self.current_pid = None
        self.telegram_settings = {
            'bot_token': '',
            'chat_id': '',
            'threshold': 500,
            'interval': 30
        }
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Разделитель для таблицы и графика
        splitter = QSplitter(Qt.Vertical)

        # Верхняя часть - таблица процессов
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)

        # Таблица процессов
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(3)
        self.process_table.setHorizontalHeaderLabels(["PID", "Имя процесса", "Память (МБ)"])
        self.process_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.process_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.process_table.setSelectionMode(QTableWidget.SingleSelection)
        self.process_table.cellDoubleClicked.connect(self.show_process_history)
        table_layout.addWidget(self.process_table)

        # Кнопки управления
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶️ Запустить мониторинг")
        self.start_btn.clicked.connect(self.start_monitoring)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹️ Остановить")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        self.settings_btn = QPushButton("⚙️ Настройки Telegram")
        self.settings_btn.clicked.connect(self.open_telegram_settings)
        btn_layout.addWidget(self.settings_btn)

        table_layout.addLayout(btn_layout)

        # Нижняя часть - график
        graph_widget = QWidget()
        graph_layout = QVBoxLayout(graph_widget)

        self.graph_label = QLabel("История использования памяти")
        self.graph_label.setAlignment(Qt.AlignCenter)
        graph_layout.addWidget(self.graph_label)

        # Холст для графика
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        graph_layout.addWidget(self.canvas)

        splitter.addWidget(table_widget)
        splitter.addWidget(graph_widget)
        splitter.setSizes([400, 300])

        main_layout.addWidget(splitter)

        # Таймер для обновления таблицы
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_process_list)
        self.update_timer.start(5000)  # Обновление каждые 5 секунд

        # Первоначальное обновление
        self.update_process_list()

    def open_telegram_settings(self):
        dialog = TelegramSettingsDialog(self)
        dialog.set_settings(self.telegram_settings)
        if dialog.exec_() == QDialog.Accepted:
            self.telegram_settings = dialog.get_settings()
            # Сохраняем настройки (в реальном приложении нужно сохранять в файл)
            QMessageBox.information(self, "Настройки сохранены",
                                    "Настройки Telegram успешно обновлены!")

    def start_monitoring(self):
        if self.is_monitoring:
            return

        # Проверка настроек Telegram
        if not self.telegram_settings.get('bot_token') or not self.telegram_settings.get('chat_id'):
            reply = QMessageBox.question(self, "Настройки Telegram",
                                         "Настройки Telegram не заданы. Хотите настроить сейчас?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.open_telegram_settings()
                return

        self.is_monitoring = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.is_monitoring = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def monitor_loop(self):
        while self.is_monitoring:
            try:
                current_time = time.time()

                for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                    try:
                        pid = proc.info['pid']
                        name = proc.info['name']
                        mem_mb = proc.info['memory_info'].rss / 1024 / 1024

                        # Сохраняем историю
                        if pid not in self.history:
                            self.history[pid] = []
                        self.history[pid].append((current_time, mem_mb))

                        # Ограничиваем длину истории
                        if len(self.history[pid]) > 100:
                            self.history[pid].pop(0)

                        # Проверка порога и отправка уведомления
                        if mem_mb > self.telegram_settings.get('threshold', 500):
                            self.send_telegram_alert(name, pid, mem_mb)

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                time.sleep(self.telegram_settings.get('interval', 30))

            except Exception as e:
                print(f"Ошибка мониторинга: {e}")
                time.sleep(5)

    def update_process_list(self):
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                mem_mb = proc.info['memory_info'].rss / 1024 / 1024
                processes.append((pid, name, mem_mb))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Сортируем по использованию памяти
        processes.sort(key=lambda x: x[2], reverse=True)

        # Обновляем таблицу
        self.process_table.setRowCount(len(processes))
        for row, (pid, name, mem_mb) in enumerate(processes):
            self.process_table.setItem(row, 0, QTableWidgetItem(str(pid)))
            self.process_table.setItem(row, 1, QTableWidgetItem(name))
            self.process_table.setItem(row, 2, QTableWidgetItem(f"{mem_mb:.1f}"))

    def show_process_history(self, row, column):
        pid = int(self.process_table.item(row, 0).text())
        name = self.process_table.item(row, 1).text()
        self.current_pid = pid
        self.plot_process_history(pid, name)

    def plot_process_history(self, pid, name):
        if pid not in self.history or not self.history[pid]:
            self.graph_label.setText(f"Нет данных истории для процесса: {name} (PID: {pid})")
            self.ax.clear()
            self.canvas.draw()
            return

        data = self.history[pid]
        times = [t for t, m in data]
        mems = [m for t, m in data]

        # Преобразуем временные метки в относительное время
        min_time = min(times)
        rel_times = [t - min_time for t in times]

        # Очищаем график
        self.ax.clear()

        # Рисуем новый график
        self.ax.plot(rel_times, mems, marker='o', linestyle='-', color='b')
        self.ax.set_title(f"История использования памяти: {name} (PID: {pid})")
        self.ax.set_xlabel("Время (сек)")
        self.ax.set_ylabel("Память (МБ)")
        self.ax.grid(True)

        # Добавляем аннотацию с текущим значением
        last_mem = mems[-1]
        self.ax.annotate(f"{last_mem:.1f} МБ",
                         xy=(rel_times[-1], last_mem),
                         xytext=(rel_times[-1] + 5, last_mem + 5),
                         arrowprops=dict(facecolor='black', shrink=0.05))

        self.graph_label.setText(f"История использования памяти: {name} (PID: {pid})")
        self.canvas.draw()

    def send_telegram_alert(self, name, pid, mem_mb):
        if not self.telegram_settings.get('bot_token') or not self.telegram_settings.get('chat_id'):
            return

        url = f"https://api.telegram.org/bot{self.telegram_settings['bot_token']}/sendMessage"
        text = (
            f"⚠️ Высокое потребление памяти!\n"
            f"Процесс: {name}\n"
            f"PID: {pid}\n"
            f"Память: {mem_mb:.1f} МБ\n"
            f"Время: {datetime.now().strftime('%H:%M:%S')}"
        )
        try:
            requests.post(url, data={
                "chat_id": self.telegram_settings['chat_id'],
                "text": text
            }, timeout=5)
        except Exception as e:
            print(f"Ошибка отправки в Telegram: {e}")