# src/camera.py
import cv2
import os
from datetime import datetime
from src.config import CAMERA_SETTINGS
import threading
import time
import tkinter as tk
from PIL import Image, ImageTk

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CameraManager:
    """Менеджер камеры для фотографирования сотрудников"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CameraManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.camera = None
        self.camera_id = CAMERA_SETTINGS.get("camera_id", 0)
        self.photo_width = CAMERA_SETTINGS.get("photo_width", 640)
        self.photo_height = CAMERA_SETTINGS.get("photo_height", 480)

        save_path = CAMERA_SETTINGS.get("save_path", "photos")
        if not os.path.isabs(save_path):
            save_path = os.path.join(BASE_DIR, save_path)
        self.save_path = save_path

        self.photo_format = CAMERA_SETTINGS.get("photo_format", "jpg")
        self.preview_duration = CAMERA_SETTINGS.get("preview_duration", 3000)
        self.flash_enabled = CAMERA_SETTINGS.get("flash_enabled", True)
        self.auto_focus = CAMERA_SETTINGS.get("auto_focus", True)
        self._camera_ready = False
        self.preview_window = None
        self._frame_lock = threading.Lock()
        self._last_frame = None
        self._last_frame_time = 0

        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

        self._capture_running = False
        self._capture_thread = None
        # ВАЖНО: поток НЕ запускаем здесь — только по явному start()

    def start(self):
        """Запустить поток захвата (вызывать ПОСЛЕ выбора camera_id)"""
        if self._capture_thread and self._capture_thread.is_alive():
            print("⚠️ Поток захвата уже запущен")
            return
        self._capture_running = True
        self._capture_thread = threading.Thread(
            target=self._capture_loop, daemon=True
        )
        self._capture_thread.start()

    def _capture_loop(self):
        """
        Единый поток: открывает камеру, прогревает и читает кадры.
        Камера открывается ЗДЕСЬ ЖЕ — иначе на Windows DSHOW read() возвращает False.
        Чтение идёт БЕЗ sleep, чтобы камера не засыпала.
        """
        print("🔄 Запущен поток захвата кадров")

        # ---------- 1. Открываем камеру в этом же потоке ----------
        try:
            self.camera = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
            if not self.camera.isOpened():
                print(f"❌ Не удалось открыть камеру {self.camera_id}")
                self._camera_ready = False
                return

            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.photo_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.photo_height)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            if self.auto_focus:
                self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)

            # ---------- 2. Прогрев: 30 кадров БЕЗ пауз ----------
            ok_warmup = 0
            for _ in range(30):
                ret, _ = self.camera.read()
                if ret:
                    ok_warmup += 1
            print(f"🔥 Прогрев: {ok_warmup}/30 кадров получено")

            self._camera_ready = True
            print(f"✅ Камера {self.camera_id} готова к работе")
        except Exception as e:
            print(f"❌ Ошибка инициализации камеры: {e}")
            self._camera_ready = False
            return

        # ---------- 3. Основной цикл: без sleep, но обновляем _last_frame не чаще 30 FPS ----------
        counter = 0
        consecutive_fail = 0
        target_fps = 30
        frame_interval = 1.0 / target_fps
        last_frame_time = time.time()

        while self._capture_running and self._camera_ready:
            try:
                if self.camera is None or not self.camera.isOpened():
                    time.sleep(0.1)
                    continue

                ret, frame = self.camera.read()

                if ret and frame is not None and frame.size > 0:
                    now = time.time()
                    if now - last_frame_time >= frame_interval:
                        # Переворот кадра по горизонтали (зеркалим)
                        frame = cv2.flip(frame, 1)

                        with self._frame_lock:
                            self._last_frame = frame.copy()
                            self._last_frame_time = now
                        last_frame_time = now
                        counter += 1
                        consecutive_fail = 0
                        if counter <= 3 or counter % 300 == 0:
                            print(f"🎞️ Кадр #{counter} захвачен (shape={frame.shape})")
                else:
                    consecutive_fail += 1
                    if consecutive_fail <= 3:
                        print(f"⚠️ _capture_loop: ret=False (сбой #{consecutive_fail})")
                    elif consecutive_fail == 10:
                        print("⚠️ _capture_loop: камера стабильно не отдаёт кадры")

                # ⚠️ БЕЗ sleep. Если нужен throttle — уже через frame_interval выше.
            except Exception as e:
                print(f"❌ Ошибка в потоке захвата: {e}")
                time.sleep(0.1)

        # ---------- 4. Освобождение ----------
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception:
                pass
            self.camera = None
        self._camera_ready = False
        print("📷 Поток захвата остановлен, камера освобождена")

    @staticmethod
    def scan_cameras(max_index=6):
        cams = []
        for idx in range(max_index):
            try:
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        h, w = frame.shape[:2]
                        cams.append({"index": idx, "width": w, "height": h})
                cap.release()
            except Exception as e:
                print(f"⚠️ Ошибка сканирования камеры {idx}: {e}")
        return cams

    @staticmethod
    def find_usb_camera(max_index=10):
        cams = CameraManager.scan_cameras(max_index=max_index)
        if not cams:
            return None
        usb_candidates = [c for c in cams if c["index"] >= 1]
        if usb_candidates:
            best = max(usb_candidates, key=lambda c: c["width"] * c["height"])
            print(f"🎯 USB-камера: index={best['index']}")
            return best["index"]
        print(f"🎯 Единственная камера: index={cams[0]['index']}")
        return cams[0]["index"]

    def get_frame(self):
        with self._frame_lock:
            if self._last_frame is not None:
                return self._last_frame.copy()
        return None

    def is_ready(self):
        return self._camera_ready and self.camera is not None and self.camera.isOpened()

    def take_photo(self, employee_name):
        if not self.is_ready():
            print("❌ Камера не готова")
            return None

        try:
            frame = None
            for attempt in range(100):
                frame = self.get_frame()
                if frame is not None and getattr(frame, "size", 0) > 0:
                    print(f"📸 Кадр получен с попытки #{attempt + 1}")
                    break
                time.sleep(0.05)

            if frame is None:
                print("❌ Не удалось получить кадр от _capture_loop за 5 секунд")
                return None
       
            now = datetime.now()
            date_folder = now.strftime("%Y-%m-%d")
            timestamp = now.strftime("%H%M%S")

            date_path = os.path.join(self.save_path, date_folder)
            if not os.path.exists(date_path):
                os.makedirs(date_path)
                print(f"📁 Создана папка: {date_path}")

            safe_name = "".join(
                c for c in employee_name
                if c.isalnum() or c in (' ', '-', '_')
            ).strip()
            filename = f"{safe_name}_{timestamp}.{self.photo_format}"
            filepath = os.path.join(date_path, filename)

            if self.photo_format.lower() == 'png':
                cv2.imwrite(filepath, frame, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            else:
                cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

            print(f"📸 Фото сохранено: {filepath}")

            return {
                "filepath": filepath,
                "filename": filename,
                "timestamp": timestamp,
                "employee_name": employee_name,
                "frame": frame
            }

        except Exception as e:
            print(f"❌ Ошибка при фотографировании: {e}")
            return None

    def show_preview(self, photo_info, root_window=None):
        try:
            if photo_info is None:
                return

            frame = photo_info.get("frame")
            if frame is None:
                frame = cv2.imread(photo_info["filepath"])
                if frame is None:
                    return
          
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            height, width = frame_rgb.shape[:2]
            max_height = 400
            max_width = 500

            if height > max_height or width > max_width:
                scale = min(max_width / width, max_height / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame_rgb = cv2.resize(frame_rgb, (new_width, new_height))
            else:
                new_width, new_height = width, height

            img = Image.fromarray(frame_rgb)
            photo = ImageTk.PhotoImage(img)

            preview_window = tk.Toplevel(root_window)
            preview_window.overrideredirect(True)
            preview_window.attributes('-topmost', True)
            preview_window.attributes('-alpha', 0.95)

            screen_width = preview_window.winfo_screenwidth()
            screen_height = preview_window.winfo_screenheight()

            preview_width = min(new_width + 40, 600)
            preview_height = min(new_height + 120, 500)

            x = screen_width - preview_width - 20
            y = screen_height - preview_height - 20

            preview_window.geometry(f"{preview_width}x{preview_height}+{x}+{y}")
            preview_window.configure(bg='#1a1a3e')

            border_frame = tk.Frame(preview_window, bg='#4CAF50', highlightthickness=2)
            border_frame.pack(expand=True, fill='both', padx=2, pady=2)

            main_frame = tk.Frame(border_frame, bg='#1a1a3e')
            main_frame.pack(expand=True, fill='both', padx=10, pady=10)

            title_frame = tk.Frame(main_frame, bg='#1a1a3e')
            title_frame.pack(fill='x', pady=(0, 5))

            name_label = tk.Label(
                title_frame,
                text=f"📸 {photo_info['employee_name']}",
                font=("Arial", 14, "bold"),
                bg='#1a1a3e',
                fg='#4CAF50'
            )
            name_label.pack(side='left')

            close_btn = tk.Button(
                title_frame,
                text="✕",
                font=("Arial", 14, "bold"),
                bg='#ff4444',
                fg='white',
                relief='flat',
                cursor='hand2',
                command=preview_window.destroy
            )
            close_btn.pack(side='right')

            def on_close_enter(e):
                close_btn.config(bg='#ff6666')

            def on_close_leave(e):
                close_btn.config(bg='#ff4444')

            close_btn.bind('<Enter>', on_close_enter)
            close_btn.bind('<Leave>', on_close_leave)

            img_label = tk.Label(main_frame, image=photo, bg='#1a1a3e')
            img_label.image = photo
            img_label.pack(pady=5)

            info_frame = tk.Frame(main_frame, bg='#1a1a3e')
            info_frame.pack(fill='x', pady=(5, 0))

            time_label = tk.Label(
                info_frame,
                text=f"⏱️ {datetime.now().strftime('%H:%M:%S')}",
                font=("Arial", 11),
                bg='#1a1a3e',
                fg='#8888aa'
            )
            time_label.pack(side='left')

            status_label = tk.Label(
                info_frame,
                text="✅ Фото сохранено",
                font=("Arial", 11, "bold"),
                bg='#1a1a3e',
                fg='#4CAF50'
            )
            status_label.pack(side='right')

            duration = CAMERA_SETTINGS.get("preview_duration", 5000)
            preview_window.after(duration, preview_window.destroy)
            preview_window.bind('<Button-1>', lambda e: preview_window.destroy())
            preview_window.bind('<Escape>', lambda e: preview_window.destroy())

            self.preview_window = preview_window

        except Exception as e:
            print(f"❌ Ошибка показа превью: {e}")

    def release(self):
        self._capture_running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=2)
            self._capture_thread = None

        if self.preview_window and self.preview_window.winfo_exists():
            try:
                self.preview_window.destroy()
            except:
                pass
            self.preview_window = None

    def __del__(self):
        self.release()


# Глобальный экземпляр (поток НЕ стартует — только по .start())
camera_manager = CameraManager()