# ui_dialogs.py
import tkinter as tk
from tkinter import font as tkfont
from src.config import ADMIN_PASSWORD
from src.virtual_keyboard import show_keyboard

class DialogManager:
    """Управление диалоговыми окнами"""
    
    def __init__(self, root, screen_width, screen_height):
        self.root = root
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.show_dialog = False
        self.dialog_window = None
        self.password_var = None
        
    def show_password_dialog(self, on_success, title="ВВЕДИТЕ ПАРОЛЬ"):
        """Показать диалог ввода пароля"""
        if self.show_dialog:
            return
            
        self.show_dialog = True
        
        # Создаем Toplevel окно
        self.dialog_window = tk.Toplevel(self.root)
        self.dialog_window.overrideredirect(True)
        
        # Центрируем окно
        dialog_width = 550
        dialog_height = 380
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
            highlightthickness=2,
            highlightcolor='#e94560'
        )
        border_frame.pack(expand=True, fill='both', padx=2, pady=2)
        
        # Основной контейнер
        main_frame = tk.Frame(border_frame, bg='#1a1a3e')
        main_frame.pack(expand=True, fill='both')
        
        # Иконка замка
        lock_label = tk.Label(
            main_frame,
            text="🔒",
            font=("Arial", 40),
            bg='#1a1a3e'
        )
        lock_label.pack(pady=(20, 5))
        
        # Заголовок
        title_label = tk.Label(
            main_frame,
            text=title,
            font=("Arial", 20, "bold"),
            bg='#1a1a3e',
            fg='white'
        )
        title_label.pack(pady=(0, 20))
        
        # Фрейм для поля ввода и кнопки клавиатуры
        input_frame = tk.Frame(main_frame, bg='#1a1a3e')
        input_frame.pack(pady=10)
        
        # Поле ввода
        self.password_var = tk.StringVar()
        password_entry = tk.Entry(
            input_frame,
            textvariable=self.password_var,
            font=("Arial", 20),
            bg='#0a0a1a',
            fg='white',
            insertbackground='white',
            show='●',
            width=15,
            justify='center',
            relief='flat',
            highlightthickness=1,
            highlightcolor='#e94560'
        )
        password_entry.pack(side='left', padx=(0, 10))
        password_entry.focus_force()
        
        # Кнопка вызова виртуальной клавиатуры
        kb_btn = tk.Label(
            input_frame,
            text="⌨️",
            font=("Arial", 18),
            bg='#2196F3',
            fg='white',
            width=3,
            height=1,
            cursor='hand2',
            anchor='center'
        )
        kb_btn.pack(side='left', ipadx=6, ipady=6)
        kb_btn.bind('<Button-1>', lambda e: show_keyboard(password_entry, self.dialog_window, "Ввод пароля"))
   
        def on_kb_enter(e):
            kb_btn.config(bg='#42a5f5')
        
        def on_kb_leave(e):
            kb_btn.config(bg='#2196F3')
        
        kb_btn.bind('<Enter>', on_kb_enter)
        kb_btn.bind('<Leave>', on_kb_leave)
        
        # Контейнер для ошибок
        error_container = tk.Frame(main_frame, bg='#1a1a3e', height=30)
        error_container.pack(fill='x', pady=5)
        
        # Кнопки
        btn_frame = tk.Frame(main_frame, bg='#1a1a3e')
        btn_frame.pack(pady=20)
        
        def check_password():
            if self.password_var.get() == ADMIN_PASSWORD:
                self.close_dialog()
                on_success()
            else:
                self.password_var.set("")
                # Показываем ошибку
                error_label = tk.Label(
                    error_container,
                    text="❌ Неправильный пароль!",
                    font=("Arial", 16),
                    bg='#1a1a3e',
                    fg='#ff4444'
                )
                error_label.pack()
                self.dialog_window.after(2000, error_label.destroy)
                password_entry.focus_force()
                
        def cancel():
            self.close_dialog()
            
        # Стиль для кнопок
        def on_btn_enter(btn, color):
            btn.config(bg=color)
            
        def on_btn_leave(btn, color):
            btn.config(bg=color)
            
        # Кнопка подтверждения
        ok_btn = tk.Button(
            btn_frame,
            text="✅ ОК",
            command=check_password,
            font=("Arial", 16, "bold"),
            bg='#4CAF50',
            fg='white',
            width=12,
            height=1,
            relief='flat',
            cursor='hand2'
        )
        ok_btn.pack(side='left', padx=10)
        
        # Кнопка отмены
        cancel_btn = tk.Button(
            btn_frame,
            text="❌ ОТМЕНА",
            command=cancel,
            font=("Arial", 16, "bold"),
            bg='#f44336',
            fg='white',
            width=12,
            height=1,
            relief='flat',
            cursor='hand2'
        )
        cancel_btn.pack(side='left', padx=10)
        
        # Эффекты наведения для кнопок
        ok_btn.bind('<Enter>', lambda e: on_btn_enter(ok_btn, '#66bb6a'))
        ok_btn.bind('<Leave>', lambda e: on_btn_leave(ok_btn, '#4CAF50'))
        cancel_btn.bind('<Enter>', lambda e: on_btn_enter(cancel_btn, '#ff6659'))
        cancel_btn.bind('<Leave>', lambda e: on_btn_leave(cancel_btn, '#f44336'))
        
        # Привязываем Enter
        password_entry.bind('<Return>', lambda e: check_password())
        self.dialog_window.bind('<Escape>', lambda e: cancel())
        
        # Предотвращаем закрытие
        self.dialog_window.protocol("WM_DELETE_WINDOW", cancel)
        
    def close_dialog(self):
        """Закрыть диалог"""
        self.show_dialog = False
        if self.dialog_window:
            try:
                self.dialog_window.destroy()
            except:
                pass
            self.dialog_window = None
        try:
            self.root.focus_force()
            self.root.lift()
        except:
            pass
        
    def show_notification(self, message, duration=1000, is_error=False):
        """Показать всплывающее уведомление"""
        color = '#ff4444' if is_error else '#4CAF50'
        bg_color = '#2a1a1a' if is_error else '#1a2a1a'
        
        # Используем Toplevel для уведомления
        notif_window = tk.Toplevel(self.root)
        notif_window.overrideredirect(True)
        
        # Центрируем уведомление
        notif_width = 600
        notif_height = 70
        x = self.screen_width//2 - notif_width//2
        y = 100
        notif_window.geometry(f"{notif_width}x{notif_height}+{x}+{y}")
        notif_window.configure(bg=bg_color)
        notif_window.attributes('-topmost', True)
        
        # Рамка
        border_frame = tk.Frame(
            notif_window,
            bg=color,
            highlightthickness=2
        )
        border_frame.pack(expand=True, fill='both', padx=2, pady=2)
        
        # Контент
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
        
        # Автоматическое закрытие
        self.root.after(duration, notif_window.destroy)