# src/face_recognition_module.py
import cv2
import numpy as np
import os
from datetime import datetime, timedelta
import threading
import time
from src.config import EMPLOYEES, APP_SETTINGS
from src.camera import camera_manager
import json

# Корень проекта — на уровень выше src (check-in/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
PHOTOS_DIR = os.path.join(BASE_DIR, "photos")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")


class FaceRecognitionModule:
    """Модуль распознавания лиц для автоматической отметки сотрудников"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(FaceRecognitionModule, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.enabled = False
        self.running = False
        self.thread = None
        self.face_cascade = None
        self.known_faces = {}
        self.last_detection = {}
        self.rejected_faces = {}
        self.callback = None
        self.frame_skip = 10
        self.frame_count = 0
        self.debug_mode = True
        self.processing_face = False
        self.root = None
        self.is_dialog_open = False

        # Последнее распознанное лицо (для отображения в диалоге)
        self.last_frame = None
        self.last_face_rect = None
        self.last_recognized_name = None

        # Загружаем порог уверенности из настроек
        self.detection_confidence = self._load_confidence()
        self._log_debug(f"📊 Порог уверенности: {self.detection_confidence}")

        # Создаём папку для логов в КОРНЕ проекта
        if not os.path.exists(LOGS_DIR):
            os.makedirs(LOGS_DIR, exist_ok=True)
            print(f"📁 Создана папка логов: {LOGS_DIR}")

        # Загружаем сохраненные лица
        self.load_known_faces()

        self._log_debug("📷 Используем камеру из camera_manager")

    def _load_confidence(self):
        """Загрузка порога уверенности из settings.json в корне проекта"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # ✅ Читаем из секции app_settings
                app_section = data.get("app_settings", {})
                confidence = app_section.get('face_recognition_confidence', 0.3)
                if 0 < confidence <= 1:
                    return confidence
            return APP_SETTINGS.get('face_recognition_confidence', 0.3)
        except Exception:
            return 0.3

    def _log_debug(self, message, level="INFO"):
        """Логирование отладочной информации в logs/face_recognition_debug.log"""
        if not self.debug_mode:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        try:
            # Убедимся, что папка существует
            if not os.path.exists(LOGS_DIR):
                os.makedirs(LOGS_DIR, exist_ok=True)

            log_file = os.path.join(LOGS_DIR, "face_recognition_debug.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            print(log_entry.strip())
        except Exception as e:
            print(f"❌ Ошибка записи лога: {e}")

    def load_known_faces(self):
        """Загрузка известных лиц из папки photos в корне проекта"""
        try:
            if not os.path.exists(PHOTOS_DIR):
                self._log_debug(f"⚠️ Папка photos не найдена: {PHOTOS_DIR}", "WARNING")
                return

            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)

            if self.face_cascade.empty():
                self._log_debug("❌ Не удалось загрузить классификатор лиц", "ERROR")
                return

            self._log_debug("✅ Классификатор лиц загружен успешно")

            count = 0
            for emp in EMPLOYEES:
                name = emp["name"]
                emp_photos = []

                for root, dirs, files in os.walk(PHOTOS_DIR):
                    for file in files:
                        if file.startswith(name) and file.endswith(('.jpg', '.jpeg', '.png')):
                            photo_path = os.path.join(root, file)
                            emp_photos.append(photo_path)

                if emp_photos:
                    self.known_faces[name] = emp_photos[0]
                    count += 1
                    self._log_debug(f"✅ Загружено лицо: {name} ({len(emp_photos)} фото)")

            self._log_debug(f"📸 Загружено {count} лиц для распознавания")

            if count == 0:
                self._log_debug("⚠️ Нет загруженных лиц! Сделайте фото сотрудников", "WARNING")

        except Exception as e:
            self._log_debug(f"❌ Ошибка загрузки лиц: {e}", "ERROR")

    def set_callback(self, callback):
        """Установка callback функции для открытия диалога"""
        self.callback = callback
        self._log_debug("✅ Callback установлен")

    def set_dialog_state(self, is_open):
        """Установка состояния диалога"""
        self.is_dialog_open = is_open
        if is_open:
            self._log_debug("🔒 Диалог открыт - распознавание приостановлено")
        else:
            self._log_debug("🔓 Диалог закрыт - распознавание возобновлено")

    def set_enabled(self, enabled):
        """Включение/отключение модуля"""
        self._log_debug(f"🔄 Установка режима enabled={enabled}")
        self.enabled = enabled
        if enabled:
            self.detection_confidence = self._load_confidence()
            self._log_debug(f"📊 Обновлен порог уверенности: {self.detection_confidence}")
            threading.Thread(target=self._delayed_start, daemon=True).start()
        else:
            self.stop()

    def _delayed_start(self):
        """Запуск с задержкой для ожидания инициализации камеры"""
        self._log_debug("⏳ Ожидание инициализации камеры...")

        max_wait = 30
        waited = 0
        while waited < max_wait:
            if camera_manager.is_ready():
                self._log_debug("✅ Камера готова, запускаем распознавание")
                self.start()
                return
            time.sleep(1)
            waited += 1
            if waited % 5 == 0:
                self._log_debug(f"⏳ Ожидание камеры... {waited} сек")

        self._log_debug("❌ Таймаут ожидания камеры", "ERROR")

    def start(self):
        """Запуск распознавания"""
        if self.running:
            self._log_debug("⚠️ Распознавание уже запущено")
            return

        if not self.known_faces:
            self._log_debug("❌ Нет загруженных лиц для распознавания", "ERROR")
            return

        if not camera_manager.is_ready():
            self._log_debug("❌ Камера не доступна", "ERROR")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self._log_debug("🔍 Модуль распознавания лиц ЗАПУЩЕН")

    def stop(self):
        """Остановка распознавания"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None
        self._log_debug("🔍 Модуль распознавания лиц остановлен")

    def _run(self):
        """Основной цикл распознавания"""
        self._log_debug("🔄 Запущен основной цикл распознавания")

        while self.running and self.enabled:
            try:
                if not camera_manager.is_ready():
                    time.sleep(1)
                    continue

                frame = camera_manager.get_frame()
                if frame is None:
                    time.sleep(0.05)
                    continue

                self.frame_count += 1
                if self.frame_count % self.frame_skip != 0:
                    time.sleep(0.01)
                    continue

                if not self.is_dialog_open:
                    self._detect_faces(frame)
                else:
                    time.sleep(0.3)

            except Exception as e:
                self._log_debug(f"❌ Ошибка в цикле: {e}", "ERROR")
                time.sleep(1)

    def _detect_faces(self, frame):
        """Обнаружение и распознавание лиц на кадре"""
        try:
            if self.processing_face:
                return

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(60, 60)
            )

            if len(faces) == 0:
                return

            for (x, y, w, h) in faces:
                face_roi = frame[y:y+h, x:x+w]

                recognized_name, confidence = self._recognize_face(face_roi)

                if recognized_name:
                    self._log_debug(f"🔍 Распознано: {recognized_name} (уверенность: {confidence:.2f})")

                    if recognized_name in self.rejected_faces:
                        reject_time = self.rejected_faces[recognized_name]
                        elapsed = (datetime.now() - reject_time).seconds
                        if elapsed < 60:
                            self._log_debug(f"⏳ Лицо {recognized_name} отклонено (осталось {60 - elapsed} сек)")
                            continue
                        else:
                            del self.rejected_faces[recognized_name]
                            self._log_debug(f"✅ Блокировка снята с {recognized_name}")

                    if recognized_name in self.last_detection:
                        last_time = self.last_detection[recognized_name]
                        if (datetime.now() - last_time).seconds < 10:
                            self._log_debug(f"⏳ Пропускаем {recognized_name} (менее 10 сек)")
                            continue

                    self.last_frame = frame.copy()
                    self.last_face_rect = (x, y, w, h)
                    self.last_recognized_name = recognized_name

                    self.last_detection[recognized_name] = datetime.now()
                    self.processing_face = True

                    self._log_debug(f"✅ ВЫЗОВ CALLBACK для {recognized_name}")

                    if self.callback and not self.is_dialog_open:
                        try:
                            self.is_dialog_open = True

                            if self.root:
                                self.root.after(5000, lambda: setattr(self, 'processing_face', False))
                            else:
                                threading.Timer(5.0, lambda: setattr(self, 'processing_face', False)).start()

                            self.callback(recognized_name)
                            self._log_debug(f"✅ Callback выполнен для {recognized_name}")
                        except Exception as e:
                            self._log_debug(f"❌ Ошибка в callback: {e}", "ERROR")
                            self.processing_face = False
                            self.is_dialog_open = False
                else:
                    if self.debug_mode and len(faces) > 0:
                        best_match, best_score = self._get_best_match(face_roi)
                        if best_match:
                            self._log_debug(f"❌ Не распознано: лучший match {best_match} (score: {best_score:.2f} < {self.detection_confidence})")

        except Exception as e:
            self._log_debug(f"❌ Ошибка детекции: {e}", "ERROR")

    def _get_best_match(self, face_roi):
        """Получить лучшее совпадение"""
        try:
            face_resized = cv2.resize(face_roi, (200, 200))
            face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)

            best_match = None
            best_score = 0

            for name, photo_path in self.known_faces.items():
                try:
                    known_img = cv2.imread(photo_path)
                    if known_img is None:
                        continue

                    known_gray = cv2.cvtColor(known_img, cv2.COLOR_BGR2GRAY)
                    known_resized = cv2.resize(known_gray, (200, 200))

                    score = self._compare_faces(face_gray, known_resized)

                    if score > best_score:
                        best_score = score
                        best_match = name

                except Exception:
                    continue

            return best_match, best_score

        except Exception:
            return None, 0.0

    def _recognize_face(self, face_roi):
        """Распознавание лица"""
        try:
            face_resized = cv2.resize(face_roi, (200, 200))
            face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)

            best_match = None
            best_score = 0

            for name, photo_path in self.known_faces.items():
                try:
                    known_img = cv2.imread(photo_path)
                    if known_img is None:
                        continue

                    known_gray = cv2.cvtColor(known_img, cv2.COLOR_BGR2GRAY)
                    known_resized = cv2.resize(known_gray, (200, 200))

                    score = self._compare_faces(face_gray, known_resized)

                    if score > best_score:
                        best_score = score
                        best_match = name

                except Exception:
                    continue

            if best_match and best_score > self.detection_confidence:
                return best_match, best_score

            return None, best_score

        except Exception:
            return None, 0.0

    def _compare_faces(self, face1, face2):
        """Сравнение лиц"""
        try:
            hist1 = cv2.calcHist([face1], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([face2], [0], None, [256], [0, 256])

            cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)

            correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            return correlation

        except Exception:
            return 0.0

    def get_last_face_image(self):
        """Возвращает последнее распознанное лицо в виде BGR numpy-массива (или None)."""
        try:
            if self.last_frame is None or self.last_face_rect is None:
                return None

            x, y, w, h = self.last_face_rect
            pad = int(0.15 * w)
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(self.last_frame.shape[1], x + w + pad)
            y2 = min(self.last_frame.shape[0], y + h + pad)

            face_crop = self.last_frame[y1:y2, x1:x2].copy()
            if face_crop.size == 0:
                return None
            return face_crop
        except Exception as e:
            self._log_debug(f"❌ Ошибка get_last_face_image: {e}", "ERROR")
            return None

    def reject_face(self, employee_name):
        """Отклонить лицо (блокировка на 1 минуту)"""
        self.rejected_faces[employee_name] = datetime.now()
        self._log_debug(f"🚫 Лицо отклонено: {employee_name} (блокировка 1 мин)")
        self.processing_face = False
        self._log_debug(f"📝 {employee_name} заблокирован на 1 минуту")

    def _log_recognition_error(self, employee_name):
        """Логирование ошибки в logs/recognition_errors.log"""
        try:
            if not os.path.exists(LOGS_DIR):
                os.makedirs(LOGS_DIR, exist_ok=True)

            log_file = os.path.join(LOGS_DIR, "recognition_errors.log")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] ❌ ОШИБКА РАСПОЗНАВАНИЯ: {employee_name}\n")
                f.write(f"  - Причина: Нажата кнопка 'ЭТО НЕ Я'\n")
                f.write(f"  - Заблокирован до: {(datetime.now() + timedelta(minutes=1)).strftime('%H:%M:%S')}\n")
                f.write("-" * 80 + "\n")

        except Exception as e:
            self._log_debug(f"❌ Ошибка записи лога: {e}", "ERROR")


# Глобальный экземпляр
face_recognition = FaceRecognitionModule()