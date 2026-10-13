# src/ui_main.py
import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime
import json
import os

from src.config import (
    EMPLOYEES, APP_SETTINGS,
    get_employee_status, get_work_time,
    get_current_weather, save_state,
)
from src.ui_dialogs import DialogManager
from src.ui_parts import PartsList
from src.ui_employee import EmployeeDialog
from src.ui_settings import SettingsDialog
from src.logo_animation import Logo3DAnimation

# Корень проекта — на уровень выше src (check-in/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")


def _load_runtime_settings():
    """Прочитать секцию app_settings из settings.json (а не весь файл!)"""
    settings = APP_SETTINGS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # ✅ Читаем именно app_settings
            settings.update(data.get("app_settings", {}))
        except Exception as e:
            print(f"⚠️ Не удалось прочитать settings.json: {e}")
    return settings

class MainUI:
    """Основной интерфейс приложения"""

    def __init__(self, root, screen_width, screen_height):
        self.root = root
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.dialog_manager = DialogManager(root, screen_width, screen_height)
        self.main_frame = None
        self.time_label = None
        self.weather_label = None
        self.employee_frames = []
        self.settings = None
        self.employee_widgets = {}
        self.logo_animation = None

        runtime = _load_runtime_settings()
        self.show_work_time_on_card = bool(runtime.get("show_work_time_on_card", True))

    def create(self):
        """Создание основного интерфейса"""
        if self.main_frame:
            self.main_frame.destroy()

        self.main_frame = tk.Frame(self.root, bg='#0a0a1a')
        self.main_frame.pack(expand=True, fill='both')

        self.create_top_panel()
        self.create_middle_section()
        self.create_exit_button()
        self.create_settings_button()

    def create_top_panel(self):
        """Создание верхней панели с временем и погодой"""
        top_panel = tk.Frame(self.main_frame, bg='#0a0a1a', height=110)
        top_panel.pack(fill='x', padx=20, pady=(10, 0))
        top_panel.pack_propagate(False)

        # ---------- Левая часть: время ----------
        time_frame = tk.Frame(top_panel, bg='#0a0a1a')
        time_frame.pack(side='left', padx=(20, 10))

        self.time_label = tk.Label(
            time_frame,
            font=("Arial", 38, "bold"),
            bg='#0a0a1a',
            fg='#e94560'
        )
        self.time_label.pack()

        # ---------- Центральная часть: логотип ----------
        logo_frame = tk.Frame(top_panel, bg='#0a0a1a')
        logo_frame.pack(side='left', padx=(10, 10), anchor='w')

        self.logo_animation = Logo3DAnimation(logo_frame, width=270, height=90)
        self.logo_animation.start()

        # ---------- Погода: справа от логотипа ----------
        weather_frame = tk.Frame(top_panel, bg='#0a0a1a')
        weather_frame.pack(side='left', padx=(5, 0), anchor='w')

        w = get_current_weather()
        weather_text = f"{w['icon']} {w['temp']} | {w['condition']} | 💧 {w['humidity']}"
    
        self.weather_label = tk.Label(
            weather_frame,
            text=weather_text,
            font=("Arial", 14),
            bg='#0a0a1a',
            fg='#ffffff',
            anchor='w',
            justify='left'
        )
        self.weather_label.pack(side='left')

        separator = tk.Frame(self.main_frame, bg='#1a1a3e', height=2)
        separator.pack(fill='x', padx=20, pady=8)

    def create_middle_section(self):
        """Создание средней части с сотрудниками и деталями"""
        middle_frame = tk.Frame(self.main_frame, bg='#0a0a1a')
        middle_frame.pack(fill='both', expand=True, padx=10, pady=5)

        right_width = 350
        parts_list = PartsList(middle_frame, right_width, self.screen_height)
        parts_list.create()

        left_frame = tk.Frame(middle_frame, bg='#0a0a1a')
        left_frame.pack(side='left', fill='both', expand=True)

        title = tk.Label(
            left_frame,
            text="👥 СОТРУДНИКИ",
            font=("Arial", 22, "bold"),
            bg='#0a0a1a',
            fg='#e94560'
        )
        title.pack(pady=(0, 6))

        grid_frame = tk.Frame(left_frame, bg='#0a0a1a')
        grid_frame.pack(expand=True, fill='both')

        cols = 5
        rows = 4

        CELL_W = 100
        CELL_H = 100
        PAD = 2

        for i in range(rows * cols):
            row = i // cols
            col = i % cols

            if i < len(EMPLOYEES):
                emp = EMPLOYEES[i]

                emp_status = get_employee_status(emp["id"])
                is_on = emp_status.get("status") == "on"

                highlight_color = '#4CAF50' if is_on else '#e94560'
                bg_color = '#1a3a1a' if is_on else '#1a1a3e'
                bd_width = 2
                highlight_width = 2

                btn_frame = tk.Frame(
                    grid_frame,
                    bg=bg_color,
                    relief='ridge',
                    bd=bd_width,
                    highlightthickness=highlight_width,
                    highlightcolor=highlight_color
                )
                btn_frame.grid(row=row, column=col, padx=PAD, pady=PAD, sticky='nsew')
                btn_frame.grid_propagate(False)
                btn_frame.config(width=CELL_W, height=CELL_H)

                status_indicator = tk.Label(
                    btn_frame,
                    text="🟢" if is_on else "⚪",
                    font=("Arial", 11),
                    bg=bg_color
                )
                status_indicator.place(x=6, y=6)

                avatar = tk.Label(
                    btn_frame,
                    text=emp["avatar"],
                    font=("Arial", 22),
                    bg=bg_color
                )
                avatar.pack(pady=(8, 0))

                name = tk.Label(
                    btn_frame,
                    text=emp["name"],
                    font=("Arial", 18, "bold"),
                    bg=bg_color,
                    fg='white'
                )
                name.pack()

                first_name = tk.Label(
                    btn_frame,
                    text=emp["first_name"],
                    font=("Arial", 9),
                    bg=bg_color,
                    fg='#8888aa'
                )
                first_name.pack()

                position = tk.Label(
                    btn_frame,
                    text=emp["position"],
                    font=("Arial", 8),
                    bg=bg_color,
                    fg='#8888aa',
                    wraplength=CELL_W - 20,
                    justify='center'
                )
                position.pack()

                time_label = None
                if is_on and self.show_work_time_on_card:
                    work_time = get_work_time(emp["id"])
                    time_label = tk.Label(
                        btn_frame,
                        text=f"⏱️ {work_time}",
                        font=("Arial", 9),
                        bg=bg_color,
                        fg='#4CAF50'
                    )
                    time_label.pack()

                btn_frame.emp_data = {
                    "id": emp["id"],
                    "frame": btn_frame,
                    "bg": bg_color,
                    "status_indicator": status_indicator,
                    "time_label": time_label,
                    "avatar": avatar,
                    "name": name,
                    "position": position
                }

                self.employee_widgets[emp["id"]] = btn_frame.emp_data

                click_handler = lambda e, emp_id=emp["id"]: self.on_employee_click(emp_id)

                for widget in (btn_frame, status_indicator, avatar, name, first_name, position):
                    widget.bind('<Button-1>', click_handler)
                    widget.configure(cursor='hand2')

                if time_label is not None:
                    time_label.bind('<Button-1>', click_handler)
                    time_label.configure(cursor='hand2')

                self.employee_frames.append(btn_frame)
            else:
                empty_frame = tk.Frame(
                    grid_frame,
                    bg='#0a0a1a',
                    relief='flat',
                    bd=0
                )
                empty_frame.grid(row=row, column=col, padx=PAD, pady=PAD, sticky='nsew')
                empty_frame.grid_propagate(False)
                empty_frame.config(width=CELL_W, height=CELL_H)

        for i in range(rows):
            grid_frame.grid_rowconfigure(i, weight=1)
        for i in range(cols):
            grid_frame.grid_columnconfigure(i, weight=1)

    def update_employee_status(self, emp_id):
        """Обновить отображение статуса сотрудника"""
        if emp_id not in self.employee_widgets:
            return

        emp_data = self.employee_widgets[emp_id]
        emp_status = get_employee_status(emp_id)
        is_on = emp_status.get("status") == "on"

        frame = emp_data["frame"]

        bg_color = '#1a3a1a' if is_on else '#1a1a3e'
        highlight_color = '#4CAF50' if is_on else '#e94560'
        bd_width = 3 if is_on else 2
        highlight_width = 3 if is_on else 2

        frame.config(bg=bg_color)
        frame.config(bd=bd_width)
        frame.config(highlightthickness=highlight_width)
        frame.config(highlightcolor=highlight_color)

        emp_data["status_indicator"].config(text="🟢" if is_on else "⚪")
        emp_data["status_indicator"].config(bg=bg_color)

        emp_data["avatar"].config(bg=bg_color)
        emp_data["name"].config(bg=bg_color)
        emp_data["position"].config(bg=bg_color)

        if is_on and self.show_work_time_on_card:
            work_time = get_work_time(emp_id)
            if emp_data["time_label"] and emp_data["time_label"].winfo_exists():
                emp_data["time_label"].config(
                    text=f"⏱️ {work_time}",
                    bg=bg_color
                )
            else:
                time_label = tk.Label(
                    frame,
                    text=f"⏱️ {work_time}",
                    font=("Arial", 9),
                    bg=bg_color,
                    fg='#4CAF50'
                )
                time_label.pack()

                click_handler = lambda e, emp_id=emp_id: self.on_employee_click(emp_id)
                time_label.bind('<Button-1>', click_handler)
                time_label.configure(cursor='hand2')

                emp_data["time_label"] = time_label
        else:
            if emp_data.get("time_label"):
                try:
                    emp_data["time_label"].destroy()
                except Exception:
                    pass
                emp_data["time_label"] = None

        for child in frame.winfo_children():
            try:
                if isinstance(child, tk.Label):
                    child.config(bg=bg_color)
            except Exception:
                pass

    def create_exit_button(self):
        """Создание кнопки выхода"""
        exit_frame = tk.Frame(self.root, bg='#0a0a1a')
        exit_frame.place(x=self.screen_width - 80, y=8)

        exit_btn = tk.Button(
            exit_frame,
            text='✕',
            font=("Arial", 28),
            bg='#2a2a4e',
            fg='#ff4444',
            relief='flat',
            bd=0,
            width=3,
            height=1,
            command=self.on_exit_click
        )
        exit_btn.pack()

        def on_enter(e):
            exit_btn.config(bg='#ff4444', fg='white')

        def on_leave(e):
            exit_btn.config(bg='#2a2a4e', fg='#ff4444')

        exit_btn.bind('<Enter>', on_enter)
        exit_btn.bind('<Leave>', on_leave)

    def create_settings_button(self):
        """Создание кнопки настроек"""
        settings_frame = tk.Frame(self.root, bg='#0a0a1a')
        settings_frame.place(x=self.screen_width - 160, y=8)

        settings_btn = tk.Button(
            settings_frame,
            text='⚙️',
            font=("Arial", 24),
            bg='#2a2a4e',
            fg='#4CAF50',
            relief='flat',
            bd=0,
            width=3,
            height=1,
            command=self.on_settings_click
        )
        settings_btn.pack()

        def on_enter(e):
            settings_btn.config(bg='#4CAF50', fg='white')

        def on_leave(e):
            settings_btn.config(bg='#2a2a4e', fg='#4CAF50')

        settings_btn.bind('<Enter>', on_enter)
        settings_btn.bind('<Leave>', on_leave)

    def on_settings_click(self):
        """Обработка клика по кнопке настроек"""
        self.root.lift()
        self.root.focus_force()

        def show_settings():
            if hasattr(self, 'dialog_manager') and self.dialog_manager.show_dialog:
                return
            self.root.after(50, self._open_settings)

        self.dialog_manager.show_password_dialog(show_settings, "ПАРОЛЬ ДЛЯ НАСТРОЕК")

    def _open_settings(self):
        """Открыть окно настроек"""
        try:
            print("Открываем настройки...")
            settings_dialog = SettingsDialog(
                self.root,
                self.screen_width,
                self.screen_height,
                self.on_settings_saved
            )
            settings_dialog.show()
            print("Настройки открыты")
        except Exception as e:
            print(f"Ошибка при открытии настроек: {e}")
            self.dialog_manager.show_notification(f"❌ Ошибка: {e}", is_error=True)

    def on_settings_saved(self, settings):
        """Обработка сохранения настроек"""
        self.settings = settings

        runtime = _load_runtime_settings()
        new_flag = bool(runtime.get("show_work_time_on_card", True))
        flag_changed = (new_flag != self.show_work_time_on_card)
        self.show_work_time_on_card = new_flag

        if flag_changed:
            self.create()

        self.dialog_manager.show_notification("✅ Настройки успешно обновлены!")

    def on_exit_click(self):
        """Обработка клика по кнопке выхода"""
        self.root.lift()
        self.root.focus_force()

        def close_app():
            print("Закрываем приложение...")
            self.root.after(100, self._close_application)

        self.dialog_manager.show_password_dialog(close_app, "ПАРОЛЬ ДЛЯ ВЫХОДА")

    def _close_application(self):
        """Закрыть приложение"""
        print("Приложение закрывается...")
        try:
            save_state()
        except Exception as e:
            print(f"⚠️ Не удалось сохранить состояние: {e}")

        try:
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            print(f"Ошибка при закрытии: {e}")
            import sys
            sys.exit(0)

    def on_employee_click(self, emp_id):
        """Обработка клика по сотруднику"""
        emp = next((e for e in EMPLOYEES if e["id"] == emp_id), None)
        if emp:
            dialog = EmployeeDialog(
                self.root,
                self.screen_width,
                self.screen_height,
                emp,
                self.on_employee_action
            )
            dialog.show()

    def on_employee_action(self, emp_id, action):
        """Обработка действия сотрудника"""
        emp = next((e for e in EMPLOYEES if e["id"] == emp_id), None)
        if emp:
            emp_status = get_employee_status(emp_id)
            is_on = emp_status.get("status") == "on"
            work_time = get_work_time(emp_id) if is_on else "00:00"

            if action == "пришел":
                message = f"✅ {emp['name']} пришел на работу"
            elif action == "ушел":
                message = f"❌ {emp['name']} ушел. Рабочее время: {work_time}"
            else:
                message = "Действие отменено"

            self.dialog_manager.show_notification(message)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

            self.update_employee_status(emp_id)

    def update_time(self):
        """Обновление времени"""
        if self.time_label and self.time_label.winfo_exists():
            current = datetime.now().strftime("%H:%M:%S")
            self.time_label.config(text=current)

    def show(self):
        """Показать интерфейс"""
        if self.main_frame:
            self.main_frame.pack(expand=True, fill='both')

    def hide(self):
        """Скрыть интерфейс"""
        if self.main_frame:
            self.main_frame.pack_forget()

    def update_weather(self):
        """Обновление погоды"""
        if self.weather_label and self.weather_label.winfo_exists():
            try:
                weather = get_current_weather()
                weather_text = (
                    f"{weather['icon']} {weather['temp']} | {weather['condition']} "
                    f"| 💧 {weather['humidity']} | 💨 {weather['wind']}"
                )
                self.weather_label.config(text=weather_text)
            except Exception as e:
                print(f"Ошибка обновления погоды: {e}")

    def destroy(self):
        """Очистка ресурсов"""
        if self.logo_animation:
            self.logo_animation.stop()
            self.logo_animation.destroy()
            self.logo_animation = None