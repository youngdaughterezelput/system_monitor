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
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal
import requests
from datetime import datetime
import json
import os


class TelegramBotManager(QObject):
    """Класс для управления Telegram ботом и обработки команд"""
    update_status_signal = pyqtSignal(bool)  # Сигнал для обновления статуса мониторинга

    def __init__(self, settings_path="telegram_settings.json"):
        super().__init__()
        self.settings_path = settings_path
        self.settings = self.load_settings()
        self.bot_thread = None
        self.is_running = False
        self.last_update_id = 0
        self._monitoring_active = False  # Внутренний флаг состояния мониторинга

    def load_settings(self):
        """Загрузка настроек из файла"""
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    return json.load(f)
            except:
                return {
                    'bot_token': '',
                    'chat_id': '',
                    'threshold': 500,
                    'interval': 30,
                    'auto_start': False
                }
        return {
            'bot_token': '',
            'chat_id': '',
            'threshold': 500,
            'interval': 30,
            'auto_start': False
        }

    @property
    def monitoring_active(self):
        return self._monitoring_active

    @monitoring_active.setter
    def monitoring_active(self, value):
        self._monitoring_active = value
        self.update_status_signal.emit(value)

    def save_settings(self, settings=None):
        """Сохранение настроек в файл"""
        if settings:
            self.settings = settings
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            return False

    def start_bot(self):
        """Запуск бота в отдельном потоке"""
        if not self.settings.get('bot_token'):
            return False

        if self.is_running:
            return True

        self.is_running = True
        self.bot_thread = threading.Thread(target=self.bot_loop, daemon=True)
        self.bot_thread.start()
        return True

    def stop_bot(self):
        """Остановка бота"""
        self.is_running = False
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=2)

    def bot_loop(self):
        """Основной цикл обработки команд бота"""
        base_url = f"https://api.telegram.org/bot{self.settings['bot_token']}/"
        get_updates_url = base_url + "getUpdates"

        while self.is_running:
            try:
                params = {'timeout': 30, 'offset': self.last_update_id + 1}
                response = requests.get(get_updates_url, params=params, timeout=35)
                data = response.json()

                if not data.get('ok'):
                    print(f"Ошибка получения обновлений: {data}")
                    time.sleep(5)
                    continue

                for update in data['result']:
                    self.last_update_id = update['update_id']

                    if 'message' in update and 'text' in update['message']:
                        message = update['message']
                        chat_id = message['chat']['id']
                        text = message['text'].strip().lower()

                        if text == '/start':
                            # Обновляем chat_id и запускаем мониторинг
                            self.settings['chat_id'] = str(chat_id)
                            self.save_settings()
                            self.monitoring_active = True

                            # Отправляем подтверждение
                            send_url = base_url + "sendMessage"
                            requests.post(send_url, data={
                                'chat_id': chat_id,
                                'text': "✅ Мониторинг запущен!\n"
                                        "Бот будет присылать уведомления о процессах с высоким потреблением памяти."
                            })
                        elif text == '/stop':
                            self.monitoring_active = False

                            # Отправляем подтверждение
                            send_url = base_url + "sendMessage"
                            requests.post(send_url, data={
                                'chat_id': chat_id,
                                'text': "⏹️ Мониторинг остановлен!"
                            })
                        elif text == '/status':
                            # Отправляем текущие настройки
                            send_url = base_url + "sendMessage"
                            status_text = (
                                f"Текущие настройки:\n"
                                f"Порог: {self.settings['threshold']} МБ\n"
                                f"Интервал: {self.settings['interval']} сек\n"
                                f"Статус мониторинга: {'активен' if self.monitoring_active else 'неактивен'}"
                            )
                            requests.post(send_url, data={
                                'chat_id': chat_id,
                                'text': status_text
                            })

                time.sleep(1)
            except requests.exceptions.RequestException as e:
                print(f"Ошибка сети бота: {e}")
                time.sleep(10)
            except Exception as e:
                print(f"Неизвестная ошибка бота: {e}")
                time.sleep(5)