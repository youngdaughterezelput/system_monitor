import psutil
import time
import threading
import requests
import json
import os
from PyQt5.QtCore import QObject, pyqtSignal


class TelegramBotManager(QObject):
    """Расширенный класс для управления Telegram ботом"""
    update_status_signal = pyqtSignal(bool)  # Сигнал статуса мониторинга
    alert_signal = pyqtSignal(str, str)  # Сигнал уведомлений (заголовок, сообщение)

    def __init__(self, settings_path="telegram_settings.json"):
        super().__init__()
        self.settings_path = settings_path
        self.settings = self.load_settings()
        self.bot_thread = None
        self.monitor_thread = None
        self.is_running = False
        self.last_update_id = 0
        self._monitoring_active = False
        self.notification_cooldown = {}  # {process_key: last_notification_time}

    def load_settings(self):
        """Загрузка настроек с дефолтными значениями"""
        default_settings = {
            'bot_token': '',
            'chat_id': '',
            'threshold': 500,  # Порог памяти в МБ
            'interval': 30,  # Интервал проверки в секундах
            'auto_start': False,  # Автозапуск мониторинга
            'whitelist': [],  # Исключенные процессы
            'cooldown_time': 3600  # Время между уведомлениями (1 час)
        }

        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    loaded = json.load(f)
                    return {**default_settings, **loaded}
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
        return default_settings

    @property
    def monitoring_active(self):
        return self._monitoring_active

    @monitoring_active.setter
    def monitoring_active(self, value):
        self._monitoring_active = value
        self.update_status_signal.emit(value)
        if value:
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            self.alert_signal.emit("Ошибка", f"Ошибка сохранения: {e}")
            return False

    def start_bot(self):
        """Запуск бота в фоновом потоке"""
        if not self.settings['bot_token']:
            self.alert_signal.emit("Ошибка", "Токен бота не установлен!")
            return False

        if self.is_running:
            return True

        self.is_running = True
        self.bot_thread = threading.Thread(target=self.bot_loop, daemon=True)
        self.bot_thread.start()

        # Автозапуск мониторинга если настроено
        if self.settings['auto_start']:
            self.monitoring_active = True

        return True

    def stop_bot(self):
        """Полная остановка бота и мониторинга"""
        self.is_running = False
        self.monitoring_active = False

        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=1.0)

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)

    def start_monitoring(self):
        """Запуск мониторинга процессов"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return

        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Остановка мониторинга процессов"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=0.5)

    def monitor_loop(self):
        """Основной цикл мониторинга потребления памяти"""
        while self._monitoring_active:
            try:
                # Сбор информации о процессах
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                    try:
                        mem_mb = proc.info['memory_info'].rss / (1024 * 1024)
                        if mem_mb > self.settings['threshold']:
                            processes.append({
                                'name': proc.info['name'],
                                'pid': proc.info['pid'],
                                'memory': f"{mem_mb:.2f} MB"
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # Фильтрация белого списка
                processes = [p for p in processes
                             if p['name'] not in self.settings['whitelist']]

                # Отправка уведомлений с кулдауном
                current_time = time.time()
                for proc in processes:
                    process_key = f"{proc['name']}_{proc['pid']}"

                    # Проверка времени последнего уведомления
                    last_notified = self.notification_cooldown.get(process_key, 0)
                    if current_time - last_notified > self.settings['cooldown_time']:
                        message = (
                            f"⚠️ Высокое потребление памяти!\n"
                            f"Процесс: {proc['name']}\n"
                            f"PID: {proc['pid']}\n"
                            f"Память: {proc['memory']}"
                        )
                        self.send_telegram_message(message)
                        self.notification_cooldown[process_key] = current_time

                time.sleep(self.settings['interval'])

            except Exception as e:
                print(f"Ошибка мониторинга: {e}")
                time.sleep(10)

    def send_telegram_message(self, message):
        """Отправка сообщения через Telegram API"""
        if not self.settings.get('chat_id'):
            return False

        try:
            url = f"https://api.telegram.org/bot{self.settings['bot_token']}/sendMessage"
            response = requests.post(url, data={
                'chat_id': self.settings['chat_id'],
                'text': message
            })
            return response.json().get('ok', False)
        except Exception as e:
            print(f"Ошибка отправки: {e}")
            return False

    def bot_loop(self):
        """Цикл обработки команд Telegram бота"""
        base_url = f"https://api.telegram.org/bot{self.settings['bot_token']}/"

        while self.is_running:
            try:
                response = requests.get(
                    f"{base_url}getUpdates",
                    params={'timeout': 30, 'offset': self.last_update_id + 1},
                    timeout=35
                )
                data = response.json()

                if not data.get('ok'):
                    time.sleep(5)
                    continue

                for update in data['result']:
                    self.last_update_id = update['update_id']
                    message = update.get('message', {})
                    text = message.get('text', '').strip().lower()

                    if not text or not message.get('chat'):
                        continue

                    chat_id = message['chat']['id']

                    # Обработка команд
                    if text == '/start':
                        self.settings['chat_id'] = str(chat_id)
                        self.save_settings()
                        self.monitoring_active = True
                        self.send_telegram_message(
                            "✅ Мониторинг запущен!\n"
                            "Бот будет присылать уведомления о процессах с высоким потреблением памяти."
                        )

                    elif text == '/stop':
                        self.monitoring_active = False
                        self.send_telegram_message("⏹️ Мониторинг остановлен!")

                    elif text == '/status':
                        status = (
                            f"Текущие настройки:\n"
                            f"• Порог: {self.settings['threshold']} МБ\n"
                            f"• Интервал: {self.settings['interval']} сек\n"
                            f"• Кулдаун: {self.settings['cooldown_time'] // 60} мин\n"
                            f"• Белый список: {', '.join(self.settings['whitelist']) or 'нет'}\n"
                            f"• Мониторинг: {'АКТИВЕН' if self.monitoring_active else 'неактивен'}"
                        )
                        self.send_telegram_message(status)

                    elif text == '/whitelist':
                        reply = message.get('reply_to_message', {})
                        reply_text = reply.get('text', '')

                        if not reply_text:
                            self.send_telegram_message(
                                "ℹ️ Для управления белым списком ответьте (reply) "
                                "на сообщение с именем процесса этой командой"
                            )
                            continue

                        # Извлекаем имя процесса из сообщения
                        proc_name = None
                        for line in reply_text.split('\n'):
                            if line.startswith('Процесс: '):
                                # Извлекаем имя после префикса
                                proc_name = line.split('Процесс: ')[1].strip()
                                break

                        if not proc_name:
                            self.send_telegram_message(
                                "❌ Не удалось определить имя процесса в сообщении\n"
                                "Убедитесь, что вы отвечаете на сообщение с уведомлением"
                            )
                            continue

                        whitelist = self.settings['whitelist']
                        action = None

                        # Удаляем PID если он есть
                        if '(' in proc_name:
                            proc_name = proc_name.split('(')[0].strip()

                        if proc_name in whitelist:
                            whitelist.remove(proc_name)
                            action = "удален из"
                        else:
                            whitelist.append(proc_name)
                            action = "добавлен в"

                        self.save_settings()
                        self.send_telegram_message(
                            f"Процесс '{proc_name}' {action} белый список\n"
                            f"Текущий список: {', '.join(whitelist) or 'пуст'}"
                        )

                time.sleep(1)

            except requests.RequestException as e:
                print(f"Ошибка сети: {e}")
                time.sleep(10)
            except Exception as e:
                print(f"Ошибка бота: {e}")
                time.sleep(5)