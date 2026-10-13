# ui_settings.py
import tkinter as tk
from tkinter import font as tkfont, ttk
from src.config import APP_SETTINGS, SETTINGS_FILE, reload_settings
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from src.virtual_keyboard import show_keyboard


class SettingsDialog:
    """Окно настроек приложения"""

    def __init__(self, root, screen_width, screen_height, on_close=None):
        self.root = root
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.on_close = on_close

        # ✅ Читаем АКТУАЛЬНЫЕ настройки из секции app_settings
        self.settings = APP_SETTINGS.copy()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.settings.update(data.get("app_settings", {}))
            except Exception as e:
                print(f"⚠️ SettingsDialog: не удалось загрузить настройки: {e}")

        self.entries = {}
        self.checkboxes = {}
        self.dialog_window = None

    def show(self):
        """Показать окно настроек"""
        # Создаем Toplevel окно
        self.dialog_window = tk.Toplevel(self.root)
        self.dialog_window.overrideredirect(True)

        # Центрируем окно
        dialog_width = 850
        dialog_height = 850
        # Позиционируем слева
        x = 20
        y = self.screen_height//2 - dialog_height//2
        self.dialog_window.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        self.dialog_window.configure(bg='#1a1a3e')
        self.dialog_window.attributes('-topmost', True)

        # Фокус и захват
        self.dialog_window.focus_force()
        self.dialog_window.grab_set()

        # Рамка с эффектом свечения
        border_frame = tk.Frame(
            self.dialog_window,
            bg='#e94560',
            highlightthickness=2
        )
        border_frame.pack(expand=True, fill='both', padx=2, pady=2)

        # Основной контейнер
        main_frame = tk.Frame(border_frame, bg='#1a1a3e')
        main_frame.pack(expand=True, fill='both')

        # Заголовок
        title = tk.Label(
            main_frame,
            text="⚙️ НАСТРОЙКИ ПРИЛОЖЕНИЯ",
            font=("Arial", 24, "bold"),
            bg='#1a1a3e',
            fg='#e94560'
        )
        title.pack(pady=20)

        # Контейнер с прокруткой
        canvas_frame = tk.Frame(main_frame, bg='#1a1a3e')
        canvas_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Создаем Canvas и Scrollbar
        canvas = tk.Canvas(
            canvas_frame,
            bg='#1a1a3e',
            highlightthickness=0,
            width=dialog_width - 60
        )
        scrollbar = tk.Scrollbar(
            canvas_frame,
            orient='vertical',
            command=canvas.yview,
            bg='#2a2a5e',
            troughcolor='#1a1a3e'
        )

        # Контейнер для виджетов
        scroll_frame = tk.Frame(canvas, bg='#1a1a3e')

        # Настройка Canvas
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw', width=dialog_width - 80)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Располагаем Canvas и Scrollbar
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Создаем виджеты настроек
        self.create_settings_widgets(scroll_frame)

        # Обновляем размеры
        scroll_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))

        # Привязываем прокрутку колесиком мыши
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind('<MouseWheel>', on_mousewheel)
        scroll_frame.bind('<MouseWheel>', on_mousewheel)

        # Кнопки управления
        btn_frame = tk.Frame(main_frame, bg='#1a1a3e')
        btn_frame.pack(pady=20)

        # Стиль для кнопок
        def on_btn_enter(btn, color):
            btn.config(bg=color)

        def on_btn_leave(btn, color):
            btn.config(bg=color)

        save_btn = tk.Button(
            btn_frame,
            text="💾СОХРАНИТЬ",
            command=self.save_settings,
            font=("Arial", 16, "bold"),
            bg='#4CAF50',
            fg='white',
            width=14,
            height=1,
            relief='flat',
            cursor='hand2'
        )
        save_btn.pack(side='left', padx=10)
        save_btn.bind('<Enter>', lambda e: on_btn_enter(save_btn, '#66bb6a'))
        save_btn.bind('<Leave>', lambda e: on_btn_leave(save_btn, '#4CAF50'))

        close_btn = tk.Button(
            btn_frame,
            text="❌ЗАКРЫТЬ",
            command=self.close,
            font=("Arial", 16, "bold"),
            bg='#f44336',
            fg='white',
            width=12,
            height=1,
            relief='flat',
            cursor='hand2'
        )
        close_btn.pack(side='left', padx=10)
        close_btn.bind('<Enter>', lambda e: on_btn_enter(close_btn, '#ff6659'))
        close_btn.bind('<Leave>', lambda e: on_btn_leave(close_btn, '#f44336'))

        exit_btn = tk.Button(
            btn_frame,
            text="ЗАКРЫТЬ ПРИЛОЖЕНИЕ",
            command=self.exit_app,
            font=("Arial", 14, "bold"),
            bg='#8B0000',
            fg='white',
            width=20,
            height=1,
            relief='flat',
            cursor='hand2'
        )
        exit_btn.pack(side='left', padx=10)
        exit_btn.bind('<Enter>', lambda e: on_btn_enter(exit_btn, '#cc0000'))
        exit_btn.bind('<Leave>', lambda e: on_btn_leave(exit_btn, '#8B0000'))

        # Закрытие по Escape
        self.dialog_window.bind('<Escape>', lambda e: self.close())

        # Предотвращаем закрытие
        self.dialog_window.protocol("WM_DELETE_WINDOW", self.close)

    def create_settings_widgets(self, parent):
        """Создание виджетов настроек"""
        # Секция: Общие настройки
        self.create_section(parent, "ОБЩИЕ НАСТРОЙКИ", 0)

        # Таймаут бездействия
        self.create_setting(
            parent, 1,
            "⏱️ Таймаут бездействия (сек):",
            "idle_timeout"
        )

        # Масштаб шрифта
        self.create_setting(
            parent, 2,
            "📏 Масштаб шрифта:",
            "font_size_scale"
        )

        # Чекбоксы
        row = 3
        self.create_checkbox(
            parent, row,
            "🎨 Включить анимацию",
            "animation_enabled"
        )

        row += 1
        self.create_checkbox(
            parent, row,
            "📸 Показывать фото сотрудников",
            "show_employee_photos"
        )

        # Добавляем чекбокс распознавания лиц
        row += 1
        self.create_checkbox(
            parent, row,
            "🔍 Включить распознавание лиц",
            "face_recognition_enabled"
        )

        # ============================================================
        # Секция: Расписание (перенесена наверх, после общих настроек)
        # ============================================================
        row += 1
        self.create_section(parent, "⏰ РАСПИСАНИЕ ОТПРАВКИ", row + 1)
        row += 2

        # Утренняя отправка
        self.create_setting(
            parent, row,
            "🌅 Утренняя отправка:",
            "email_send_time_morning"
        )
        row += 1

        # Вечерняя отправка
        self.create_setting(
            parent, row,
            "🌇 Вечерняя отправка:",
            "email_send_time_evening"
        )
        row += 1

        # Автоотправка
        self.create_checkbox(
            parent, row,
            "🔄 Автоматическая отправка отчетов",
            "auto_send_reports"
        )

        # Кнопка ручной отправки
        row += 1
        manual_frame = tk.Frame(parent, bg='#1a1a3e')
        manual_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=10, padx=10)

        send_btn = tk.Button(
            manual_frame,
            text="📨 ОТПРАВИТЬ ОТЧЕТ СЕЙЧАС",
            command=self.send_report_now,
            font=("Arial", 14, "bold"),
            bg='#FF9800',
            fg='white',
            width=30,
            height=1,
            relief='flat',
            cursor='hand2'
        )
        send_btn.pack()

        def on_send_btn_enter(e):
            send_btn.config(bg='#FFA726')

        def on_send_btn_leave(e):
            send_btn.config(bg='#FF9800')

        send_btn.bind('<Enter>', on_send_btn_enter)
        send_btn.bind('<Leave>', on_send_btn_leave)

        hint_label = tk.Label(
            manual_frame,
            text="(Отправить отчет за сегодня прямо сейчас)",
            font=("Arial", 11),
            bg='#1a1a3e',
            fg='#8888aa'
        )
        hint_label.pack(pady=(5, 0))

        # ============================================================
        # Секция: Email настройки (перенесена вниз)
        # ============================================================
        row += 1
        self.create_section(parent, "📧 НАСТРОЙКИ EMAIL", row + 1)
        row += 2

        # SMTP сервер
        self.create_setting(
            parent, row,
            "🌐 SMTP сервер:",
            "email_smtp_server"
        )
        row += 1

        # SMTP порт
        self.create_setting(
            parent, row,
            "🔌 SMTP порт:",
            "email_smtp_port"
        )
        row += 1

        # Отправитель
        self.create_setting(
            parent, row,
            "📤 Email отправителя:",
            "email_sender"
        )
        row += 1

        # Пароль email
        self.create_setting(
            parent, row,
            "🔑 Пароль email:",
            "email_password",
            is_password=True
        )
        row += 1

        # Получатель
        self.create_setting(
            parent, row,
            "📥 Email получателя:",
            "email_receiver"
        )
        row += 1

        # Кнопка тестовой отправки
        test_frame = tk.Frame(parent, bg='#1a1a3e')
        test_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=10, padx=10)

        test_btn = tk.Button(
            test_frame,
            text="📧 ТЕСТОВАЯ ОТПРАВКА ПИСЬМА",
            command=self.send_test_email,
            font=("Arial", 14, "bold"),
            bg='#2196F3',
            fg='white',
            width=30,
            height=1,
            relief='flat',
            cursor='hand2'
        )
        test_btn.pack()

        def on_test_btn_enter(e):
            test_btn.config(bg='#42a5f5')

        def on_test_btn_leave(e):
            test_btn.config(bg='#2196F3')

        test_btn.bind('<Enter>', on_test_btn_enter)
        test_btn.bind('<Leave>', on_test_btn_leave)

        hint_label = tk.Label(
            test_frame,
            text="(Проверка настроек email перед сохранением)",
            font=("Arial", 11),
            bg='#1a1a3e',
            fg='#8888aa'
        )
        hint_label.pack(pady=(5, 0))

    def send_report_now(self):
        """Ручная отправка отчета"""
        # ✅ ИСПРАВЛЕНО: импорт от корня проекта
        from src.report_generator import report_generator
        self.show_notification("⏳ Отправка отчета...")
        success = report_generator.send_report()
        if success:
            self.show_notification("✅ Отчет успешно отправлен!")
        else:
            self.show_notification("❌ Ошибка отправки отчета!", is_error=True)

    def create_section(self, parent, title, row):
        """Создание секции"""
        section = tk.Frame(parent, bg='#1a1a3e')
        section.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(15, 5), padx=10)

        label = tk.Label(
            section,
            text=title,
            font=("Arial", 16, "bold"),
            bg='#1a1a3e',
            fg='#e94560'
        )
        label.pack(anchor='w')

        # Разделитель
        sep = tk.Frame(parent, bg='#2a2a5e', height=2)
        sep.grid(row=row+1, column=0, columnspan=2, sticky='ew', pady=(5, 10), padx=10)

    def create_setting(self, parent, row, label_text, key, is_password=False):
        """Создание строки настройки с кнопкой клавиатуры"""
        # Контейнер для строки
        row_frame = tk.Frame(parent, bg='#1a1a3e')
        row_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=5, padx=10)

        # Метка
        label = tk.Label(
            row_frame,
            text=label_text,
            font=("Arial", 14),
            bg='#1a1a3e',
            fg='white',
            anchor='w',
            width=25
        )
        label.pack(side='left', padx=(0, 10))

        # Фрейм для поля ввода и кнопки клавиатуры
        input_frame = tk.Frame(row_frame, bg='#1a1a3e')
        input_frame.pack(side='left', fill='x', expand=True)

        # Поле ввода
        entry_var = tk.StringVar()
        entry_var.set(str(self.settings.get(key, "")))

        entry = tk.Entry(
            input_frame,
            textvariable=entry_var,
            font=("Arial", 14),
            bg='#0a0a1a',
            fg='white',
            insertbackground='white',
            width=25,
            show='●' if is_password else '',
            relief='flat',
            highlightthickness=1,
            highlightcolor='#e94560'
        )
        entry.pack(side='left', fill='x', expand=True)

        # Кнопка клавиатуры (для всех полей)
        kb_btn = tk.Button(
            input_frame,
            text="⌨️",
            font=("Arial", 12),
            bg='#2196F3',
            fg='white',
            relief='flat',
            cursor='hand2',
            width=3,
            command=lambda: show_keyboard(entry, self.dialog_window, f"Ввод: {label_text}")
        )
        kb_btn.pack(side='left', padx=(5, 0))

        def on_kb_enter(e):
            kb_btn.config(bg='#42a5f5')

        def on_kb_leave(e):
            kb_btn.config(bg='#2196F3')

        kb_btn.bind('<Enter>', on_kb_enter)
        kb_btn.bind('<Leave>', on_kb_leave)

        self.entries[key] = entry_var

    def create_checkbox(self, parent, row, text, key):
        """Создание чекбокса"""
        var = tk.BooleanVar()
        var.set(self.settings.get(key, False))

        checkbox = tk.Checkbutton(
            parent,
            text=text,
            variable=var,
            font=("Arial", 14),
            bg='#1a1a3e',
            fg='white',
            selectcolor='#1a1a3e',
            activebackground='#1a1a3e',
            anchor='w'
        )
        checkbox.grid(row=row, column=0, columnspan=2, sticky='w', pady=5, padx=10)

        self.checkboxes[key] = var

    def send_test_email(self):
        """Отправка тестового письма"""
        try:
            # Собираем текущие значения из полей
            smtp_server = self.entries.get("email_smtp_server", tk.StringVar()).get()
            smtp_port = self.entries.get("email_smtp_port", tk.StringVar()).get()
            sender = self.entries.get("email_sender", tk.StringVar()).get()
            password = self.entries.get("email_password", tk.StringVar()).get()
            receiver = self.entries.get("email_receiver", tk.StringVar()).get()

            # Проверяем заполненность полей
            if not all([smtp_server, smtp_port, sender, password, receiver]):
                self.show_notification("❌ Заполните все поля email!", is_error=True)
                return

            # Создаем сообщение
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = receiver
            msg['Subject'] = "🔧 Тестовое письмо от Терминала"

            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .header {{ color: #e94560; font-size: 24px; font-weight: bold; }}
                    .content {{ margin: 20px 0; }}
                    .footer {{ color: #888; font-size: 12px; margin-top: 30px; }}
                </style>
            </head>
            <body>
                <div class="header">✅ Тестовое письмо</div>
                <div class="content">
                    <p>Это тестовое письмо отправлено из Терминала учета сотрудников.</p>
                    <p>📅 Дата и время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
                    <p>⚙️ Настройки email работают корректно!</p>
                </div>
                <div class="footer">
                    Это автоматическое сообщение, не отвечайте на него.
                </div>
            </body>
            </html>
            """

            msg.attach(MIMEText(body, 'html'))

            # Отправляем письмо
            self.show_notification("⏳ Отправка тестового письма...")

            try:
                with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                    server.starttls()
                    server.login(sender, password)
                    server.send_message(msg)

                self.show_notification("✅ Тестовое письмо успешно отправлено!")

            except smtplib.SMTPAuthenticationError:
                self.show_notification("❌ Ошибка авторизации! Проверьте логин/пароль", is_error=True)
            except smtplib.SMTPConnectError:
                self.show_notification("❌ Не удалось подключиться к серверу! Проверьте настройки", is_error=True)
            except smtplib.SMTPException as e:
                self.show_notification(f"❌ Ошибка SMTP: {str(e)}", is_error=True)
            except Exception as e:
                self.show_notification(f"❌ Ошибка отправки: {str(e)}", is_error=True)

        except Exception as e:
            self.show_notification(f"❌ Ошибка: {str(e)}", is_error=True)

    def save_settings(self):
        """Сохранение настроек"""
        try:
            # Собираем данные
            for key, var in self.entries.items():
                value = var.get()
                if key == "idle_timeout" or key == "email_smtp_port":
                    try:
                        value = int(value)
                    except:
                        value = 0
                elif key == "font_size_scale":
                    try:
                        value = float(value)
                    except:
                        value = 1.0
                self.settings[key] = value

            for key, var in self.checkboxes.items():
                self.settings[key] = var.get()

            self.save_config_file()
            self.show_notification("✅ Настройки сохранены!")

            # ✅ Обновляем глобальные переменные config (на случай,
            # если что-то поменялось и в других секциях)
            try:
                reload_settings()
            except Exception as e:
                print(f"⚠️ reload_settings: {e}")

            if self.on_close:
                self.on_close(self.settings)

        except Exception as e:
            self.show_notification(f"❌ Ошибка сохранения: {str(e)}", is_error=True)

    def save_config_file(self):
        """Сохранить настройки, НЕ затирая employees/parts/camera_settings"""
        try:
            # ✅ Читаем существующий файл
            existing = {}
            if os.path.exists(SETTINGS_FILE):
                try:
                    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                except Exception as e:
                    print(f"⚠️ Не удалось прочитать settings.json: {e}")

            # ✅ Обновляем ТОЛЬКО секцию app_settings
            existing["app_settings"] = self.settings

            # Если других секций нет — подставим дефолты (чтобы файл был валидным)
            existing.setdefault("employees", [])
            existing.setdefault("parts", [])
            existing.setdefault("camera_settings", {})
            existing.setdefault("admin_password", "123")

            # ✅ Пишем обратно
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            print(f"💾 Настройки сохранены: {SETTINGS_FILE}")
        except Exception as e:
            print(f"❌ Ошибка сохранения файла: {e}")

    def close(self):
        """Закрытие окна настроек"""
        if self.dialog_window:
            self.dialog_window.destroy()
            self.dialog_window = None
        # Возвращаем фокус главному окну
        try:
            if self.root.winfo_exists():
                self.root.focus_force()
                self.root.lift()
        except:
            pass

    def exit_app(self):
        """Закрытие приложения"""
        self.close()
        self.root.quit()
        self.root.destroy()

    def show_notification(self, message, is_error=False):
        """Показать уведомление"""
        color = '#ff4444' if is_error else '#4CAF50'
        bg_color = '#2a1a1a' if is_error else '#1a2a1a'

        notif = tk.Toplevel(self.root)
        notif.overrideredirect(True)
        notif.geometry(f"500x60+{self.screen_width//2-250}+{self.screen_height//2-30}")
        notif.configure(bg=bg_color)
        notif.attributes('-topmost', True)

        # Рамка
        border_frame = tk.Frame(
            notif,
            bg=color,
            highlightthickness=2
        )
        border_frame.pack(expand=True, fill='both', padx=2, pady=2)

        content_frame = tk.Frame(border_frame, bg=bg_color)
        content_frame.pack(expand=True, fill='both')

        label = tk.Label(
            content_frame,
            text=message,
            font=("Arial", 18),
            bg=bg_color,
            fg=color
        )
        label.pack(expand=True)

        self.root.after(3000, notif.destroy)