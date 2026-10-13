# src/scheduler.py
import threading
import time
import json
import os
from datetime import datetime, timedelta

from src.report_generator import report_generator
from src.config import APP_SETTINGS

# Корень проекта — на уровень выше src (check-in/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")


class ReportScheduler:
    """Планировщик отправки отчетов"""

    def __init__(self):
        self.running = False
        self.thread = None
        self.settings = APP_SETTINGS.copy()
        self.last_morning_sent = None
        self.last_evening_sent = None

    def start(self):
        """Запуск планировщика"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("📅 Планировщик отчетов запущен")

    def stop(self):
        """Остановка планировщика"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("📅 Планировщик отчетов остановлен")

    def _run(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                self._check_schedule()
            except Exception as e:
                print(f"❌ Ошибка в планировщике: {e}")
            time.sleep(30)  # Проверяем каждые 30 секунд

    def _check_schedule(self):
        """Проверка расписания"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        # Загружаем свежие настройки
        self._load_settings()

        if not self.settings.get("auto_send_reports", True):
            return

        morning_time = self.settings.get("email_send_time_morning", "09:00")
        evening_time = self.settings.get("email_send_time_evening", "20:00")

        # Утренняя отправка
        if current_time == morning_time:
            if self.last_morning_sent != now.strftime("%Y-%m-%d"):
                print(f"🌅 Отправка утреннего отчета в {current_time}")
                success = report_generator.send_report()
                if success:
                    self.last_morning_sent = now.strftime("%Y-%m-%d")

        # Вечерняя отправка
        if current_time == evening_time:
            if self.last_evening_sent != now.strftime("%Y-%m-%d"):
                print(f"🌇 Отправка вечернего отчета в {current_time}")
                success = report_generator.send_report()
                if success:
                    self.last_evening_sent = now.strftime("%Y-%m-%d")

    def _load_settings(self):
        """Загрузка настроек из settings.json в корне проекта"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except Exception as e:
                print(f"⚠️ Scheduler: не удалось загрузить settings.json: {e}")


# Глобальный экземпляр
scheduler = ReportScheduler()