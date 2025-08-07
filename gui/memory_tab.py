import os

import psutil
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QHeaderView, QSplitter, QComboBox,
    QMessageBox, QInputDialog, QDialog, QFormLayout, QLineEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
import requests
from datetime import datetime
from tgBotManager import TelegramBotManager
from crypto_utils import SecretManager

class MemoryTab(QWidget):
    def __init__(self):
        super().__init__()
        self.is_monitoring = False
        self.monitor_thread = None
        self.history = {}  # {pid: [(time, mem_mb), ...]}
        self.current_pid = None

        # Инициализация менеджера бота
        self.bot_manager = TelegramBotManager()
        self.telegram_settings = self.bot_manager.settings

        # Подключение сигналов бота
        self.bot_manager.update_status_signal.connect(self.set_monitoring_state)

        self.init_ui()

        # Автозапуск бота при старте, если настроено
        if self.telegram_settings.get('auto_start', False) and self.telegram_settings.get('bot_token'):
            self.bot_manager.start_bot()

    def set_monitoring_state(self, active):
        """Устанавливает состояние мониторинга (вызывается из бота)"""
        if active and not self.is_monitoring:
            self.start_monitoring()
        elif not active and self.is_monitoring:
            self.stop_monitoring()

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
        self.start_btn.clicked.connect(lambda: self.set_monitoring_state(True))
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹️ Остановить")
        self.stop_btn.clicked.connect(lambda: self.set_monitoring_state(False))
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        self.bot_status_label = QLabel("Статус бота: ❌ Неактивен")
        btn_layout.addWidget(self.bot_status_label)

        self.monitor_status_label = QLabel("Мониторинг: ❌ Неактивен")
        btn_layout.addWidget(self.monitor_status_label)

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

        # Обновление статуса бота
        self.update_bot_status()

    def open_telegram_settings(self):
        dialog = TelegramSettingsDialog(self, self.telegram_settings)
        if dialog.exec_() == QDialog.Accepted:
            new_settings = dialog.get_settings()

            # Сохраняем настройки
            self.bot_manager.save_settings(new_settings)
            self.telegram_settings = self.bot_manager.settings

            # Перезапускаем бота, если настройки изменились
            if new_settings.get('bot_token'):
                self.bot_manager.stop_bot()
                if new_settings.get('auto_start', False):
                    self.bot_manager.start_bot()

            self.update_bot_status()

            QMessageBox.information(self, "Настройки сохранены",
                                    "Настройки Telegram успешно обновлены!")

    def update_bot_status(self):
        """Обновление статуса бота в интерфейсе"""
        if self.bot_manager.is_running:
            self.bot_status_label.setText("Статус бота: ✅ Активен")
            self.bot_status_label.setStyleSheet("color: green;")
        else:
            self.bot_status_label.setText("Статус бота: ❌ Неактивен")
            self.bot_status_label.setStyleSheet("color: red;")

    def update_monitor_status(self):
        """Обновление статуса мониторинга в интерфейсе"""
        if self.is_monitoring:
            self.monitor_status_label.setText("Мониторинг: ✅ Активен")
            self.monitor_status_label.setStyleSheet("color: green;")
        else:
            self.monitor_status_label.setText("Мониторинг: ❌ Неактивен")
            self.monitor_status_label.setStyleSheet("color: red;")

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
        self.update_monitor_status()

        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

        # Запускаем бота, если он еще не запущен
        if not self.bot_manager.is_running and self.telegram_settings.get('bot_token'):
            self.bot_manager.start_bot()
            self.update_bot_status()

    def stop_monitoring(self):
        self.is_monitoring = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.update_monitor_status()

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

    def send_telegram_alert(self, name, pid, mem_mb):
        """Отправка уведомления через бота"""
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

    def closeEvent(self, event):
        """Остановка бота при закрытии вкладки"""
        self.bot_manager.stop_bot()
        self.stop_monitoring()
        event.accept()


class TelegramSettingsDialog(QDialog):
    """Диалоговое окно для настройки Telegram уведомлений с защитой от изменений"""

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки Telegram")
        self.setFixedSize(450, 300)

        # Инициализируем менеджер секретов
        self.secret_manager = SecretManager()

        # Зашифрованные дефолтные значения (получите их один раз через encrypt_secrets.py)
        self.encrypted_defaults = {
            'bot_token': 'gAAAAABolJxA0cu8FNEVjGQyx8C3CqrwRpdzHEecUwtzOu4bzIAau5q6WVom4GCGrGc5gHGtjT4CKFFzmi_krXeWBV0Yp8Semf38GhtmB96K8rhI6fDEOxsfO9XB42XnL9us7QGU_cVM',  # Ваш зашифрованный токен
            'chat_id': 'gAAAAABolJxAxlYxgrhypwMeMNHg-ScfBUuDho3snLvJQHsCHnhZomZ__dxEGrRkuMSAYeZKnG_2FhYqjE0OtLa_t4ZhwhLLLA=='  # Ваш зашифрованный chat_id
        }

        self.default_settings = {
            'bot_token': self.secret_manager.decrypt(self.encrypted_defaults['bot_token']),
            'chat_id': self.secret_manager.decrypt(self.encrypted_defaults['chat_id']),
            'threshold': 500,
            'interval': 30,
            'auto_start': False
        }

        self.current_settings = settings if settings else self.default_settings.copy()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Чекбокс для разрешения редактирования
        self.edit_checkbox = QCheckBox("Разрешить редактирование настроек")
        self.edit_checkbox.stateChanged.connect(self.toggle_editing)
        layout.addWidget(self.edit_checkbox)

        # Форма с настройками
        form_layout = QFormLayout()

        # Токен бота
        self.bot_token_edit = QLineEdit()
        self.bot_token_edit.setPlaceholderText("Введите токен бота")
        form_layout.addRow("Токен бота:", self.bot_token_edit)

        # ID чата
        self.chat_id_edit = QLineEdit()
        self.chat_id_edit.setPlaceholderText("Введите ID чата")
        form_layout.addRow("ID чата/канала:", self.chat_id_edit)

        # Порог памяти
        self.threshold_edit = QLineEdit()
        self.threshold_edit.setPlaceholderText("500")
        form_layout.addRow("Порог памяти (МБ):", self.threshold_edit)

        # Интервал сканирования
        self.interval_edit = QLineEdit()
        self.interval_edit.setPlaceholderText("30")
        form_layout.addRow("Интервал сканирования (сек):", self.interval_edit)

        # Автозапуск
        self.auto_start_check = QComboBox()
        self.auto_start_check.addItems(["Выключен", "Включен"])
        form_layout.addRow("Автозапуск с приложением:", self.auto_start_check)

        layout.addLayout(form_layout)

        # Кнопки управления
        btn_layout = QHBoxLayout()

        # Кнопка сброса
        self.reset_btn = QPushButton("Сбросить к дефолтным")
        self.reset_btn.clicked.connect(self.reset_to_default)
        btn_layout.addWidget(self.reset_btn)

        # Кнопки сохранения/отмены
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Устанавливаем текущие настройки
        self.set_settings(self.current_settings)
        self.toggle_editing(False)  # По умолчанию поля неактивны

    def toggle_editing(self, state):
        """Активирует/деактивирует поля для редактирования"""
        enabled = bool(state)
        self.bot_token_edit.setEnabled(enabled)
        self.chat_id_edit.setEnabled(enabled)
        self.threshold_edit.setEnabled(enabled)
        self.interval_edit.setEnabled(enabled)
        self.auto_start_check.setEnabled(enabled)
        self.reset_btn.setEnabled(enabled)

    def reset_to_default(self):
        """Сбрасывает настройки к дефолтным значениям"""
        reply = QMessageBox.question(
            self,
            "Сброс настроек",
            "Вы уверены, что хотите сбросить настройки к значениям по умолчанию?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.set_settings(self.default_settings)

            # Очищаем файл с настройками, если он существует
            settings_file = "telegram_settings.json"
            if os.path.exists(settings_file):
                try:
                    os.remove(settings_file)
                    QMessageBox.information(
                        self,
                        "Настройки сброшены",
                        "Настройки успешно сброшены к значениям по умолчанию."
                    )
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        f"Не удалось удалить файл настроек: {str(e)}"
                    )

    def get_settings(self):
        """Возвращает текущие настройки"""
        return {
            'bot_token': self.bot_token_edit.text().strip(),
            'chat_id': self.chat_id_edit.text().strip(),
            'threshold': int(self.threshold_edit.text()) if self.threshold_edit.text().strip() else 500,
            'interval': int(self.interval_edit.text()) if self.interval_edit.text().strip() else 30,
            'auto_start': self.auto_start_check.currentIndex() == 1
        }

    def set_settings(self, settings):
        """Устанавливает настройки в форму"""
        self.bot_token_edit.setText(settings.get('bot_token', ''))
        self.chat_id_edit.setText(settings.get('chat_id', ''))
        self.threshold_edit.setText(str(settings.get('threshold', 500)))
        self.interval_edit.setText(str(settings.get('interval', 30)))
        self.auto_start_check.setCurrentIndex(1 if settings.get('auto_start', False) else 0)

        # Сохраняем текущие настройки
        self.current_settings = settings