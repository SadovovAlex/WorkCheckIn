# main.py
import tkinter as tk
from datetime import datetime
import json
import os

from src.config import APP_SETTINGS, EMPLOYEES, CAMERA_SETTINGS, SETTINGS_FILE
from src.ui_main import MainUI
from src.ui_employee import EmployeeDialog
from src.utils import IdleMonitor, TimeManager, AnimationManager
from src.camera import CameraManager
from src.face_recognition_module import face_recognition


class TouchTerminalApp:
    """Главное приложение"""

    def __init__(self):
        self.root = tk.Tk()

        # Загружаем настройки
        self.load_settings()

        # Получаем размеры экрана
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # Настройка окна
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.tk.call('tk', 'scaling', self.settings.get('font_size_scale', 1.5))
        self.root.configure(bg='#0a0a1a')

        self.root.lift()
        self.root.focus_force()

        self.protect_from_minimize()

        self.main_ui = MainUI(self.root, self.screen_width, self.screen_height)
        self.main_ui.create()

        idle_timeout = self.settings.get('idle_timeout', 10)
        self.idle_monitor = IdleMonitor(
            timeout_callback=self.on_idle_timeout,
            reset_callback=self.on_idle_reset,
            timeout=idle_timeout
        )
        self.idle_monitor.start()

        self.update_time()
        self.update_employee_times()

         # ✅ Периодическое обновление погоды
        self.update_weather()                        # первый вызов сразу
        self.schedule_weather_update()               # ← повтор каждые 15 минут


        if self.settings.get('animation_enabled', True):
            self.start_star_animation()

        self.autodetect_camera()
        self.init_camera()
        self.init_face_recognition()

        from src.scheduler import scheduler
        scheduler.start()

        self.root.bind('<Button-1>', self.on_touch)
        self.root.bind('<Escape>', lambda e: self.main_ui.on_exit_click())
        self.root.bind('<Key>', self.on_key_press)

    # ---------- НАСТРОЙКИ ----------
    def load_settings(self):
        """Загрузка настроек из settings.json (секция app_settings).

        ВАЖНО: settings.json теперь имеет вложенную структуру:
            {
              "employees": [...],
              "parts": [...],
              "camera_settings": {...},
              "app_settings": {...},
              "admin_password": "..."
            }
        Нам нужна только секция app_settings.
        """
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)

                # Берём секцию app_settings (а не весь файл целиком!)
                app_section = loaded.get("app_settings", {})
                APP_SETTINGS.update(app_section)
            except Exception as e:
                print(f"⚠️ Не удалось загрузить settings.json: {e}")

        self.settings = APP_SETTINGS

    # ---------- КАМЕРА ----------
    def init_camera(self):
        from src.camera import camera_manager
        print(f"📷 Открываем камеру id={CAMERA_SETTINGS.get('camera_id', 0)}...")
        camera_manager.start()
        import time
        for _ in range(50):
            if camera_manager.is_ready():
                print("✅ Камера готова (main)")
                return
            time.sleep(0.1)
        print("⚠️ Камера не открылась за 5 секунд")

    def autodetect_camera(self):
        if self.settings.get("camera_id_lock", False):
            print(f"📷 camera_id зафиксирован: {CAMERA_SETTINGS['camera_id']}")
            return

        try:
            cams = CameraManager.scan_cameras(max_index=6)
        except Exception as e:
            print(f"⚠️ Ошибка сканирования камер: {e}")
            return

        if not cams:
            print("❌ Камеры не найдены — оставляем текущий camera_id")
            return

        preferred = CAMERA_SETTINGS.get("camera_id", 0)
        if any(c["index"] == preferred for c in cams):
            print(f"✅ Используем настроенный camera_id={preferred}")
            return

        usb = [c for c in cams if c["index"] >= 1]
        if usb:
            best = max(usb, key=lambda c: c["width"] * c["height"])
            CAMERA_SETTINGS["camera_id"] = best["index"]
            print(f"🎯 Автовыбор USB-камеры: id={best['index']} "
                  f"({best['width']}x{best['height']})")
            return

        CAMERA_SETTINGS["camera_id"] = cams[0]["index"]
        print(f"🎯 Автовыбор камеры: id={cams[0]['index']}")

    # ---------- РАСПОЗНАВАНИЕ ЛИЦ ----------
    def init_face_recognition(self):
        face_recognition.root = self.root
        face_recognition.set_callback(self.on_face_recognized)

        if self.settings.get('face_recognition_enabled', False):
            face_recognition.set_enabled(True)
            print("🔍 Распознавание лиц включено")
        else:
            print("🔍 Распознавание лиц отключено в настройках")

    def on_face_recognized(self, employee_name):
        print(f"🔍 РАСПОЗНАН: {employee_name}")
        employee = next((e for e in EMPLOYEES if e["name"] == employee_name), None)

        if employee:
            if hasattr(self, 'main_ui') and hasattr(self.main_ui, 'dialog_manager'):
                if self.main_ui.dialog_manager.show_dialog:
                    print(f"⏳ Диалог уже открыт, пропускаем {employee_name}")
                    return
            self.root.after(0, lambda: self.show_employee_dialog(employee))

    def show_employee_dialog(self, employee):
        print(f"📱 Открытие диалога для: {employee['name']}")
        try:
            dialog = EmployeeDialog(
                self.root,
                self.screen_width,
                self.screen_height,
                employee,
                self.main_ui.on_employee_action
            )
            dialog.show()
        except Exception as e:
            print(f"❌ Ошибка открытия диалога: {e}")

    # ---------- ПРОЧЕЕ ----------
    def update_weather(self):
        if hasattr(self, 'main_ui') and hasattr(self.main_ui, 'update_weather'):
            try:
                self.main_ui.update_weather()
            except Exception as e:
                print(f"Ошибка обновления погоды: {e}")

    def schedule_weather_update(self):
        """Планирует обновление погоды каждые 15 минут (900 000 мс)"""
        WEATHER_UPDATE_INTERVAL_MS = 15 * 60 * 1000   # 15 минут

        def _do_update():
            try:
                self.update_weather()
                # Обновляем глобальный WEATHER в config, чтобы idle-экран тоже видел свежие данные
                import src.config as _cfg
                _cfg.WEATHER = _cfg.get_weather()
            except Exception as e:
                print(f"⚠️ Ошибка обновления погоды: {e}")
            finally:
                self.root.after(WEATHER_UPDATE_INTERVAL_MS, _do_update)

        self.root.after(WEATHER_UPDATE_INTERVAL_MS, _do_update)  

    def update_employee_times(self):
        from src.config import get_employee_status, get_work_time

        if hasattr(self, 'main_ui'):
            for frame in self.main_ui.employee_frames:
                if hasattr(frame, 'emp_data'):
                    emp_id = frame.emp_data["id"]
                    emp_status = get_employee_status(emp_id)
                    is_on = emp_status.get("status") == "on"

                    if is_on:
                        work_time = get_work_time(emp_id)
                        for child in frame.winfo_children():
                            if isinstance(child, tk.Label) and "⏱️" in child.cget("text"):
                                child.config(text=f"⏱️ {work_time}")
                                break

        try:
            self.root.after(10000, self.update_employee_times)
        except:
            pass

    def protect_from_minimize(self):
        self.root.bind('<Alt-F4>', lambda e: "break")
        self.root.bind('<Alt-Tab>', lambda e: "break")
        self.root.bind('<Super_L>', lambda e: "break")
        self.root.bind('<Super_R>', lambda e: "break")

    def start_star_animation(self):
        def should_animate():
            return not self.idle_monitor.is_idle and self.settings.get('animation_enabled', True)

        anim = AnimationManager.create_stars(
            self.root,
            self.screen_width,
            self.screen_height,
            should_animate
        )
        anim()

    def on_idle_timeout(self):
        if hasattr(self, 'main_ui'):
            if hasattr(self.main_ui, 'dialog_manager') and self.main_ui.dialog_manager.show_dialog:
                return
        self.root.after(0, self.show_idle_screen)

    def on_idle_reset(self):
        self.root.after(0, self.hide_idle_screen)

    def show_idle_screen(self):
        self.main_ui.hide()

        self.idle_frame = tk.Frame(self.root, bg='#0a0a1a')
        self.idle_frame.pack(expand=True, fill='both')

        self.idle_time_label = tk.Label(
            self.idle_frame,
            font=("Arial", 120, "bold"),
            bg='#0a0a1a',
            fg='#e94560'
        )
        self.idle_time_label.pack(expand=True)

        self.idle_date_label = tk.Label(
            self.idle_frame,
            font=("Arial", 36),
            bg='#0a0a1a',
            fg='#8888aa'
        )
        self.idle_date_label.pack()

        from src.config import get_current_weather
        w = get_current_weather()
        weather_text = f"{w['icon']} {w['temp']} | {w['condition']}"
        weather_label = tk.Label(
            self.idle_frame,
            text=weather_text,
            font=("Arial", 32),
            bg='#0a0a1a',
            fg='white'
        )
        weather_label.pack(pady=10)

        hint = tk.Label(
            self.idle_frame,
            text="👆 Нажмите на экран для продолжения",
            font=("Arial", 24),
            bg='#0a0a1a',
            fg='#666688'
        )
        hint.pack(pady=20)

        self.update_idle_time()

    def update_idle_time(self):
        if hasattr(self, 'idle_frame') and self.idle_frame.winfo_exists():
            current = TimeManager.get_current_time()
            date = TimeManager.get_current_date()
            try:
                self.idle_time_label.config(text=current)
                self.idle_date_label.config(text=date)
            except:
                pass
            self.root.after(1000, self.update_idle_time)

    def hide_idle_screen(self):
        if hasattr(self, 'idle_frame'):
            self.idle_frame.destroy()
            delattr(self, 'idle_frame')
        self.main_ui.show()

    def update_time(self):
        self.main_ui.update_time()
        self.root.after(1000, self.update_time)

    def on_touch(self, event):
        self.idle_monitor.reset()

    def on_key_press(self, event):
        self.idle_monitor.reset()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = TouchTerminalApp()
    app.run()