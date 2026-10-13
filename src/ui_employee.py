# src/ui_employee.py
import tkinter as tk
from tkinter import font as tkfont
import numpy as np
import cv2
from PIL import Image, ImageTk
from src.config import get_employee_status, set_employee_status, get_work_time, CAMERA_SETTINGS
from src.camera import camera_manager
from src.face_recognition_module import face_recognition
import threading
import os
from datetime import datetime, timedelta


class EmployeeDialog:
    """Диалог выбора действия для сотрудника"""

    def __init__(self, root, screen_width, screen_height, employee, callback):
        self.root = root
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.employee = employee
        self.callback = callback
        self.dialog_window = None
        self.timer_id = None
        self.timeout_seconds = 15
        self.remaining_seconds = self.timeout_seconds
        self.timer_label = None
        self.photo_label = None
        self._fresh_photo_taken = False

        # Устанавливаем состояние диалога в модуле распознавания
        face_recognition.set_dialog_state(True)

    def show(self):
        """Показать диалог"""
        self.dialog_window = tk.Toplevel(self.root)
        self.dialog_window.overrideredirect(True)

        dialog_width = 860
        dialog_height = 620
        x = self.screen_width // 2 - dialog_width // 2
        y = self.screen_height // 2 - dialog_height // 2
        self.dialog_window.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        self.dialog_window.configure(bg='#1a1a3e')
        self.dialog_window.attributes('-topmost', True)

        self.dialog_window.focus_force()
        self.dialog_window.grab_set()

        border_frame = tk.Frame(
            self.dialog_window,
            bg='#e94560',
            highlightthickness=2
        )
        border_frame.pack(expand=True, fill='both', padx=2, pady=2)

        main_frame = tk.Frame(border_frame, bg='#1a1a3e')
        main_frame.pack(expand=True, fill='both', padx=30, pady=30)

        content_frame = tk.Frame(main_frame, bg='#1a1a3e')
        content_frame.pack(expand=True, fill='both')

        # ---------- ЛЕВАЯ КОЛОНКА: ФОТО ----------
        photo_frame = tk.Frame(content_frame, bg='#1a1a3e', width=260)
        photo_frame.pack(side='left', fill='y', padx=(0, 25))
        photo_frame.pack_propagate(False)

        self.photo_label = tk.Label(
            photo_frame,
            bg='#1a1a3e',
            text="",
            borderwidth=0,
            highlightthickness=2,
            highlightbackground='#e94560'
        )
        self.photo_label.pack(expand=True)

        self.photo_label.config(
            text=self.employee.get("avatar", "👤"),
            font=("Arial", 80),
            fg='white'
        )

        self._take_fresh_photo_async()

        # ---------- ПРАВАЯ КОЛОНКА: ИНФОРМАЦИЯ ----------
        right_frame = tk.Frame(content_frame, bg='#1a1a3e')
        right_frame.pack(side='left', expand=True, fill='both')

        info_frame = tk.Frame(right_frame, bg='#1a1a3e')
        info_frame.pack(pady=10, anchor='w')

        name = tk.Label(
            info_frame,
            text=self.employee["name"],
            font=("Arial", 28, "bold"),
            bg='#1a1a3e',
            fg='white',
            anchor='w'
        )
        name.pack(anchor='w')

        position = tk.Label(
            info_frame,
            text=self.employee["position"],
            font=("Arial", 18),
            bg='#1a1a3e',
            fg='#8888aa',
            anchor='w'
        )
        position.pack(anchor='w')

        status_frame = tk.Frame(right_frame, bg='#1a1a3e')
        status_frame.pack(pady=10, anchor='w')

        emp_status = get_employee_status(self.employee["id"])
        current_status = emp_status.get("status", "off")
        work_time = get_work_time(self.employee["id"]) if current_status == "on" else "00:00"

        status_text = "🟢 НА РАБОТЕ" if current_status == "on" else "⚪ НЕ НА РАБОТЕ"
        status_color = "#4CAF50" if current_status == "on" else "#888888"

        status_label = tk.Label(
            status_frame,
            text=status_text,
            font=("Arial", 18, "bold"),
            bg='#1a1a3e',
            fg=status_color,
            anchor='w'
        )
        status_label.pack(anchor='w')

        time_label = tk.Label(
            status_frame,
            text=f"⏱️ Рабочее время: {work_time}",
            font=("Arial", 16),
            bg='#1a1a3e',
            fg='#e94560',
            anchor='w'
        )
        time_label.pack(anchor='w', pady=5)

        # ---------- КНОПКИ ПРИШЕЛ / УШЕЛ ----------
        btn_frame = tk.Frame(right_frame, bg='#1a1a3e')
        btn_frame.pack(pady=20, anchor='w')

        def on_action(action):
            if action == "пришел":
                set_employee_status(self.employee["id"], "on")
                self.take_employee_photo(self.employee["name"], "приход")
                if face_recognition.enabled:
                    face_recognition.reject_face(self.employee["name"])
                    print(f"🔒 {self.employee['name']} заблокирован на 1 минуту (приход)")

            elif action == "ушел":
                set_employee_status(self.employee["id"], "off")
                self.take_employee_photo(self.employee["name"], "уход")
                if face_recognition.enabled:
                    face_recognition.reject_face(self.employee["name"])
                    print(f"🔒 {self.employee['name']} заблокирован на 1 минуту (уход)")

            elif action == "отмена":
                if face_recognition.enabled:
                    face_recognition.reject_face(self.employee["name"])
                    print(f"🚫 Лицо {self.employee['name']} заблокировано на 1 минуту (ЭТО НЕ Я)")

            self._stop_timer()
            self.close()
            if self.callback:
                self.callback(self.employee["id"], action)

        def on_timeout():
            self._stop_timer()
            self.close()
            if self.callback:
                self.callback(self.employee["id"], "таймаут")

        def on_btn_enter(btn, color):
            btn.config(bg=color)

        def on_btn_leave(btn, color):
            btn.config(bg=color)

        arrived_btn = tk.Button(
            btn_frame,
            text="✅ ПРИШЕЛ",
            command=lambda: on_action("пришел"),
            font=("Arial", 22, "bold"),
            bg='#4CAF50',
            fg='white',
            width=10,
            height=3,
            relief='flat',
            cursor='hand2'
        )
        arrived_btn.pack(side='left', padx=8)
        arrived_btn.bind('<Enter>', lambda e: on_btn_enter(arrived_btn, '#66bb6a'))
        arrived_btn.bind('<Leave>', lambda e: on_btn_leave(arrived_btn, '#4CAF50'))

        left_btn = tk.Button(
            btn_frame,
            text="❌ УШЕЛ",
            command=lambda: on_action("ушел"),
            font=("Arial", 22, "bold"),
            bg='#f44336',
            fg='white',
            width=10,
            height=3,
            relief='flat',
            cursor='hand2'
        )
        left_btn.pack(side='left', padx=8)
        left_btn.bind('<Enter>', lambda e: on_btn_enter(left_btn, '#ff6659'))
        left_btn.bind('<Leave>', lambda e: on_btn_leave(left_btn, '#f44336'))

        bottom_frame = tk.Frame(right_frame, bg='#1a1a3e')
        bottom_frame.pack(side='bottom', fill='x', pady=(10, 0))

        self.timer_label = tk.Label(
            bottom_frame,
            text=f"⏱️ Автозакрытие через {self.remaining_seconds} сек",
            font=("Arial", 12),
            bg='#1a1a3e',
            fg='#8888aa'
        )
        self.timer_label.pack(side='left')

        cancel_btn = tk.Button(
            bottom_frame,
            text="↩️ НАЗАД",
            command=lambda: on_action("отмена"),
            font=("Arial", 16, "bold"),
            bg='#333333',
            fg='white',
            width=10,
            height=2,
            relief='flat',
            cursor='hand2'
        )
        cancel_btn.pack(side='right')
        cancel_btn.bind('<Enter>', lambda e: on_btn_enter(cancel_btn, '#555555'))
        cancel_btn.bind('<Leave>', lambda e: on_btn_leave(cancel_btn, '#333333'))

        top_right_frame = tk.Frame(border_frame, bg='#1a1a3e')
        top_right_frame.place(relx=1.0, x=-10, y=10, anchor='ne')

        not_me_btn = tk.Button(
            top_right_frame,
            text="🚫 ЭТО НЕ Я",
            command=lambda: on_action("отмена"),
            font=("Arial", 14, "bold"),
            bg='#ff4444',
            fg='white',
            padx=15,
            pady=8,
            relief='flat',
            cursor='hand2'
        )
        not_me_btn.pack()

        def on_not_me_enter(e):
            not_me_btn.config(bg='#ff6666')

        def on_not_me_leave(e):
            not_me_btn.config(bg='#ff4444')

        not_me_btn.bind('<Enter>', on_not_me_enter)
        not_me_btn.bind('<Leave>', on_not_me_leave)

        self._start_timer(on_timeout)

        self.dialog_window.bind('<Escape>', lambda e: on_action("отмена"))
        self.dialog_window.protocol("WM_DELETE_WINDOW", lambda: on_action("отмена"))

    def _take_fresh_photo_async(self):
        """Сделать свежий снимок с камеры в фоне и показать его"""
        if self._fresh_photo_taken:
            return
        self._fresh_photo_taken = True

        def task():
            frame = None
            try:
                if camera_manager.is_ready():
                    if hasattr(camera_manager, "grab_frame"):
                        frame = camera_manager.grab_frame()
                    else:
                        if hasattr(camera_manager, "get_frame"):
                            frame = camera_manager.get_frame()
            except Exception as e:
                print(f"⚠️ Ошибка получения свежего кадра: {e}")

            if frame is None:
                try:
                    frame = face_recognition.get_last_face_image()
                except Exception as e:
                    print(f"⚠️ Ошибка get_last_face_image: {e}")
                    frame = None

            try:
                self.root.after(0, lambda: self._apply_photo(frame))
            except Exception:
                pass

        threading.Thread(target=task, daemon=True).start()

    def _apply_photo(self, frame_bgr):
        """Показать кадр в photo_label (вызывается из главного потока)"""
        if self.photo_label is None:
            return
        try:
            if not self.photo_label.winfo_exists():
                return
        except Exception:
            return

        if frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
            return

        try:
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

            target = 220
            h, w = frame_rgb.shape[:2]
            if h == 0 or w == 0:
                return

            scale = target / max(h, w)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            frame_resized = cv2.resize(frame_rgb, (new_w, new_h))

            canvas = np.full((target, target, 3), (26, 26, 62), dtype=np.uint8)
            y_off = (target - new_h) // 2
            x_off = (target - new_w) // 2
            canvas[y_off:y_off + new_h, x_off:x_off + new_w] = frame_resized

            pil_img = Image.fromarray(canvas)
            tk_img = ImageTk.PhotoImage(pil_img)

            self.photo_label.config(image=tk_img, text="")
            self.photo_label.image = tk_img
        except Exception as e:
            print(f"⚠️ Ошибка отображения свежего снимка: {e}")

    def _start_timer(self, timeout_callback):
        self.remaining_seconds = self.timeout_seconds
        self._update_timer(timeout_callback)

    def _update_timer(self, timeout_callback):
        if self.remaining_seconds <= 0:
            timeout_callback()
            return

        if self.timer_label and self.timer_label.winfo_exists():
            if self.remaining_seconds <= 5:
                color = '#ff4444'
            elif self.remaining_seconds <= 10:
                color = '#ffaa00'
            else:
                color = '#8888aa'

            self.timer_label.config(
                text=f"⏱️ Автозакрытие через {self.remaining_seconds} сек",
                fg=color
            )

        self.remaining_seconds -= 1

        if self.dialog_window and self.dialog_window.winfo_exists():
            self.timer_id = self.dialog_window.after(1000, lambda: self._update_timer(timeout_callback))

    def _stop_timer(self):
        if self.timer_id:
            try:
                self.dialog_window.after_cancel(self.timer_id)
            except:
                pass
            self.timer_id = None

    def take_employee_photo(self, employee_name, action):
        """Сделать фото сотрудника в отдельном потоке"""
        def photo_task():
            try:
                if not camera_manager.is_ready():
                    print(f"⚠️ Камера не готова для {employee_name}")
                    return

                photo_info = camera_manager.take_photo(employee_name)

                if photo_info:
                    camera_manager.show_preview(photo_info, self.root)
                    print(f"📸 Фото {employee_name} ({action}) сохранено: {photo_info['filename']}")
                else:
                    print(f"❌ Не удалось сфотографировать {employee_name}")

            except Exception as e:
                print(f"❌ Ошибка фотографирования: {e}")

        thread = threading.Thread(target=photo_task, daemon=True)
        thread.start()

    def close(self):
        self._stop_timer()

        try:
            face_recognition.set_dialog_state(False)
            face_recognition.processing_face = False
        except:
            pass

        if self.dialog_window:
            self.dialog_window.destroy()
            self.dialog_window = None
        try:
            if self.root.winfo_exists():
                self.root.focus_force()
                self.root.lift()
        except:
            pass